import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, TextContent

from stagespirit_mcp import __version__
from stagespirit_mcp.runtime.models import RuntimeSummary

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_discovery_status_and_unknown_tool(server_parameters: StdioServerParameters) -> None:
    schema = json.loads((ROOT / "contracts/schemas/runtime-summary.schema.json").read_text("utf-8"))
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
        async with stdio_client(server_parameters, errlog=errors) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=10) as session:
                initialization = await session.initialize()
                assert initialization.protocol_version == "2025-11-25"
                assert initialization.server_info.name == "StageSpirit"
                assert initialization.server_info.version == __version__
                listing = await session.list_tools()
                assert [tool.name for tool in listing.tools] == [
                    "runtime_status",
                    "settings_get",
                    "settings_save",
                    "settings_apply",
                    "operation_get",
                ]
                assert listing.next_cursor is None
                resources = await session.list_resources()
                assert resources.resources == [] and resources.next_cursor is None
                templates = await session.list_resource_templates()
                assert templates.resource_templates == [] and templates.next_cursor is None
                prompts = await session.list_prompts()
                assert prompts.prompts == [] and prompts.next_cursor is None
                tool = listing.tools[0]
                assert tool.input_schema["properties"] == {}
                assert tool.output_schema == {k: v for k, v in schema.items() if k != "$schema"}
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.title == "运行状态"
                result = await session.call_tool("runtime_status", {})
                assert not result.is_error
                assert result.structured_content is not None
                Draft202012Validator(schema, format_checker=FormatChecker()).validate(
                    result.structured_content
                )
                RuntimeSummary.model_validate(result.structured_content)
                assert len(result.content) == 1
                assert isinstance(result.content[0], TextContent)
                assert json.loads(result.content[0].text) == result.structured_content
                assert result.structured_content["modules"] == [
                    {"name": "runtime", "state": "ready"},
                    {"name": "settings", "state": "ready"},
                ]
                with pytest.raises(MCPError) as unknown:
                    await session.call_tool("missing_tool", {})
                assert unknown.value.code == INVALID_PARAMS
                again = await session.call_tool("runtime_status")
                assert (
                    again.structured_content["instance_id"]
                    == result.structured_content["instance_id"]
                )
                assert (
                    again.structured_content["uptime_ms"] >= result.structured_content["uptime_ms"]
                )
        errors.seek(0)
        assert errors.read() == ""


@pytest.mark.asyncio
async def test_stdio_restart_preserves_generation(server_parameters: StdioServerParameters) -> None:
    snapshots = []
    for _ in range(2):
        async with stdio_client(server_parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=10) as session:
                await session.initialize()
                snapshots.append((await session.call_tool("runtime_status")).structured_content)
    assert snapshots[0]["data_generation"] == snapshots[1]["data_generation"]
    assert snapshots[0]["instance_id"] != snapshots[1]["instance_id"]


@pytest.mark.asyncio
async def test_wire_errors_and_utf8(server_parameters: StdioServerParameters) -> None:
    process = await asyncio.create_subprocess_exec(
        server_parameters.command,
        *server_parameters.args,
        cwd=server_parameters.cwd,
        env=os.environ | server_parameters.env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def request(message: dict) -> dict:
        process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        await process.stdin.drain()
        raw = await asyncio.wait_for(process.stdout.readline(), 10)
        assert raw
        response = json.loads(raw.decode("utf-8"))
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == message["id"]
        return response

    try:
        initialized = await request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "stagespirit-test", "version": "1"},
                },
            }
        )
        assert initialized["result"]["protocolVersion"] == "2025-11-25"
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        await process.stdin.drain()
        unknown = await request({"jsonrpc": "2.0", "id": 2, "method": "unknown_method"})
        assert unknown["error"]["code"] == -32601
        invalid = await request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "runtime_status", "arguments": []},
            }
        )
        assert invalid["error"]["code"] == -32602
        listing = await request({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})
        assert listing["result"]["tools"][0]["title"] == "运行状态"
        status = await request(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "runtime_status", "arguments": {}},
            }
        )
        assert status["result"]["structuredContent"]["profile_id"] == "default"
        process.stdin.close()
        await asyncio.wait_for(process.wait(), 10)
        assert process.returncode == 0
        assert await process.stdout.read() == b""
        assert "Traceback" not in (await process.stderr.read()).decode("utf-8")
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


@pytest.mark.parametrize("profile", ["default", "../bad"])
def test_cli_eof_and_startup_error(tmp_path: Path, profile: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stagespirit_mcp",
            "serve",
            "--profile",
            profile,
            "--data-dir",
            str(tmp_path / "中文 数据"),
        ],
        input=b"",
        capture_output=True,
        timeout=20,
        env=os.environ | {"PYTHONIOENCODING": "gbk", "PYTHONUTF8": "0"},
        cwd=tmp_path,
    )
    assert result.stdout == b""
    if profile == "default":
        assert result.returncode == 0
        assert result.stderr == b""
    else:
        assert result.returncode == 1
        assert "运行配置 ID" in result.stderr.decode("utf-8")
        assert "Traceback" not in result.stderr.decode("utf-8")
