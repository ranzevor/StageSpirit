"""Save runtime settings in an isolated profile and confirm recovery after restart."""

import asyncio
import json
import sys
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    with TemporaryDirectory(prefix="stagespirit-settings-") as directory:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "stagespirit_mcp", "serve", "--data-dir", directory],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                status = await session.call_tool("runtime_status", {})
                if status.is_error or status.structured_content is None:
                    raise RuntimeError("无法读取运行状态。")
                configuration = await session.call_tool("settings_get", {"section": "runtime"})
                if configuration.is_error or configuration.structured_content is None:
                    raise RuntimeError("无法读取配置。")
                saved = await session.call_tool(
                    "settings_save",
                    {
                        "section": "runtime",
                        "data_generation": status.structured_content["data_generation"],
                        "expected_revision": configuration.structured_content["saved_revision"],
                        "changes": {"log_level": "ERROR"},
                    },
                )
                if saved.is_error:
                    raise RuntimeError("运行配置保存或应用失败。")
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                restored = await session.call_tool("settings_get", {"section": "runtime"})
                if restored.is_error or restored.structured_content is None:
                    raise RuntimeError("无法读取恢复后的运行配置。")
                if restored.structured_content["active_values"] != {"log_level": "ERROR"}:
                    raise RuntimeError("运行配置尚未生效。")
                print(json.dumps(restored.structured_content, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
