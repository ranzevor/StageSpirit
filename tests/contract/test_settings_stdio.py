import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "contracts/schemas"
REGISTRY = Registry().with_resources(
    (path.as_uri(), Resource.from_contents(json.loads(path.read_text("utf-8"))))
    for path in SCHEMAS.glob("*.schema.json")
)


def check_result(result, schema: str) -> dict:
    assert result.structured_content is not None
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert json.loads(result.content[0].text) == result.structured_content
    name, _, fragment = schema.partition("#")
    uri = (SCHEMAS / f"{name}.schema.json").as_uri()
    if fragment:
        uri += f"#{fragment}"
    Draft202012Validator({"$ref": uri}, registry=REGISTRY, format_checker=FormatChecker()).validate(
        result.structured_content
    )
    return result.structured_content


@pytest.mark.asyncio
async def test_settings_discovery_save_apply_and_operation(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            for name in ("settings_get", "settings_save", "settings_apply", "operation_get"):
                request_schema = json.loads(
                    (SCHEMAS / f"{name.replace('_', '-')}-request.schema.json").read_text("utf-8")
                )
                assert tools[name].input_schema == {
                    key: value for key, value in request_schema.items() if key != "$schema"
                }
            assert tools["settings_get"].annotations.read_only_hint
            assert not tools["settings_save"].annotations.read_only_hint
            assert tools["settings_apply"].annotations.idempotent_hint
            generation = (await session.call_tool("runtime_status", {})).structured_content[
                "data_generation"
            ]
            initial = check_result(
                await session.call_tool("settings_get", {"section": "runtime"}), "settings-section"
            )
            assert initial["values"] == initial["active_values"] == {"log_level": "WARNING"}
            saved_result = await session.call_tool(
                "settings_save",
                {
                    "section": "runtime",
                    "data_generation": generation,
                    "expected_revision": 0,
                    "changes": {"log_level": "ERROR"},
                },
            )
            saved = check_result(saved_result, "configuration-receipt")
            assert not saved_result.is_error
            assert saved["saved_revision"] == saved["active_revision"] == 1
            assert saved["application_state"] == "applied"
            arguments = {
                "section": "runtime",
                "data_generation": generation,
                "revision": 1,
                "idempotency_key": "应用-配置",
            }
            result = await session.call_tool("settings_apply", arguments)
            applied = check_result(result, "common#/$defs/OperationReceipt")
            assert not result.is_error and applied["state"] == "completed"
            duplicate = check_result(
                await session.call_tool("settings_apply", arguments),
                "common#/$defs/OperationReceipt",
            )
            assert applied == duplicate
            detail = check_result(
                await session.call_tool("operation_get", {"operation_id": applied["operation_id"]}),
                "operation-detail",
            )
            assert detail["effect_state"] == "confirmed"
            assert detail["execution_generation"] == 1


@pytest.mark.asyncio
async def test_settings_business_errors_preserve_connection_and_values(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            generation = (await session.call_tool("runtime_status", {})).structured_content[
                "data_generation"
            ]
            valid = {
                "section": "runtime",
                "data_generation": generation,
                "expected_revision": 0,
                "changes": {"log_level": "ERROR"},
            }
            cases = [
                ("settings_save", valid | {"expected_revision": True}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"changes": {}}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"changes": {"log_level": None}}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"changes": {"token": "synthetic"}}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"extra": "synthetic"}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"section": "speech"}, "INVALID_ARGUMENT"),
                ("settings_save", valid | {"scope_id": "other"}, "INVALID_ARGUMENT"),
                (
                    "settings_save",
                    valid | {"data_generation": "old", "expected_revision": 99},
                    "DATA_GENERATION_CHANGED",
                ),
                ("settings_save", valid | {"expected_revision": 99}, "REVISION_CONFLICT"),
                (
                    "settings_apply",
                    {
                        "section": "runtime",
                        "data_generation": generation,
                        "revision": 99,
                        "idempotency_key": "stale",
                    },
                    "REVISION_CONFLICT",
                ),
                ("operation_get", {"operation_id": "not-in-this-profile"}, "NOT_FOUND"),
            ]
            for name, arguments, code in cases:
                result = await session.call_tool(name, arguments)
                body = check_result(result, "common#/$defs/Error")
                assert result.is_error and body["code"] == code
                if code == "DATA_GENERATION_CHANGED":
                    assert body["context"]["current_data_generation"] == generation
            after = check_result(
                await session.call_tool("settings_get", {"section": "runtime"}), "settings-section"
            )
            assert after["saved_revision"] == after["active_revision"] == 0
            assert after["values"] == {"log_level": "WARNING"}


@pytest.mark.asyncio
async def test_stdio_saved_configuration_recovers_after_process_restart(
    server_parameters: StdioServerParameters,
) -> None:
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            generation = (await session.call_tool("runtime_status", {})).structured_content[
                "data_generation"
            ]
            saved = check_result(
                await session.call_tool(
                    "settings_save",
                    {
                        "section": "runtime",
                        "data_generation": generation,
                        "expected_revision": 0,
                        "changes": {"log_level": "ERROR"},
                    },
                ),
                "configuration-receipt",
            )
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            current = check_result(
                await session.call_tool("settings_get", {"section": "runtime"}), "settings-section"
            )
            assert current["saved_revision"] == current["active_revision"] == 1
            assert current["values"] == current["active_values"] == {"log_level": "ERROR"}
            assert current["data_generation"] == generation
            old = await session.call_tool(
                "operation_get", {"operation_id": saved["apply_operation_id"]}
            )
            assert not old.is_error
            assert check_result(old, "operation-detail")["state"] == "completed"


@pytest.mark.asyncio
async def test_failed_application_preserves_receipt_and_read_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from stagespirit_mcp.bootstrap.application import open_runtime
    from stagespirit_mcp.entrypoints.mcp import create_server
    from stagespirit_mcp.runtime.configuration import RuntimeSettings

    with open_runtime("default", tmp_path) as runtime:
        server = create_server(runtime)
        original = runtime.configuration.activate

        def fail(candidate):
            if isinstance(candidate, RuntimeSettings) and candidate.log_level == "ERROR":
                raise RuntimeError("injected MCP activation failure")
            original(candidate)

        with monkeypatch.context() as patch:
            patch.setattr(runtime.configuration, "activate", fail)
            failed = await server.call_tool(
                "settings_save",
                {
                    "section": "runtime",
                    "data_generation": runtime.data_generation,
                    "expected_revision": 0,
                    "changes": {"log_level": "ERROR"},
                },
            )
        body = check_result(failed, "configuration-receipt")
        assert failed.is_error
        assert body["saved_revision"] == 1 and body["active_revision"] == 0
        assert body["error"]["code"] == "CONFIGURATION_APPLY_FAILED"
        query = await server.call_tool("settings_get", {"section": "runtime"})
        assert not query.is_error
        current = check_result(query, "settings-section")
        assert current["values"] == {"log_level": "ERROR"}
        assert current["active_values"] == {"log_level": "WARNING"}
        operation = await server.call_tool(
            "operation_get", {"operation_id": body["apply_operation_id"]}
        )
        assert not operation.is_error
        assert check_result(operation, "operation-detail")["state"] == "failed"
