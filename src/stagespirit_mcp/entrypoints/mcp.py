from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, CallToolResult, InputRequiredResult, ToolAnnotations

from stagespirit_mcp import __version__
from stagespirit_mcp.runtime.service import RuntimeInstance


class StageSpiritServer(MCPServer[None]):
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[None, Any] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        if not any(tool.name == name for tool in await self.list_tools()):
            raise MCPError(code=INVALID_PARAMS, message="工具不存在。")
        return await super().call_tool(name, arguments, context)


def create_server(runtime: RuntimeInstance) -> MCPServer[None]:
    server = StageSpiritServer(
        "StageSpirit",
        version=__version__,
        log_level="WARNING",
    )
    server.add_tool(
        runtime.snapshot,
        name="runtime_status",
        title="运行状态",
        description="读取当前运行配置、数据代际、实例身份和已启动模块的固定摘要。",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    return server
