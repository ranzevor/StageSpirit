"""Connect to an isolated StageSpirit process and print its runtime status."""

import asyncio
import json
import sys
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    with TemporaryDirectory(prefix="stagespirit-example-") as directory:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "stagespirit_mcp", "serve", "--data-dir", directory],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                if "runtime_status" not in {tool.name for tool in tools.tools}:
                    raise RuntimeError("服务未提供 runtime_status。")
                result = await session.call_tool("runtime_status", {})
                if result.is_error or result.structured_content is None:
                    raise RuntimeError("运行状态查询失败。")
                print(json.dumps(result.structured_content, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
