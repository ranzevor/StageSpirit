import json
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from mcp.types import (
    INVALID_PARAMS,
    CallToolResult,
    InputRequiredResult,
    TextContent,
    ToolAnnotations,
)
from mcp.types import (
    Tool as MCPTool,
)
from pydantic import BaseModel, ConfigDict, ValidationError

from stagespirit_mcp import __version__
from stagespirit_mcp.modules.settings.models import (
    ConfigurationReceipt,
    ConfigurationSection,
    DataGeneration,
    IdempotencyKey,
    OperationGetRequest,
    Revision,
    RuntimeSettingsChanges,
    ScopeId,
    SectionName,
    SettingsApplyRequest,
    SettingsGetRequest,
    SettingsSaveRequest,
)
from stagespirit_mcp.runtime.configuration import RuntimeSettings
from stagespirit_mcp.runtime.contracts import Error, OperationDetail, OperationReceipt
from stagespirit_mcp.runtime.errors import BusinessError
from stagespirit_mcp.runtime.service import RuntimeInstance


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


_REQUEST_MODELS: dict[str, type[BaseModel]] = {
    "runtime_status": EmptyRequest,
    "settings_get": SettingsGetRequest,
    "settings_save": SettingsSaveRequest,
    "settings_apply": SettingsApplyRequest,
    "operation_get": OperationGetRequest,
}


def error_result(error: Error) -> CallToolResult:
    body = error.model_dump(mode="json", exclude_none=True)
    return CallToolResult(
        content=[TextContent(type="text", text=error.model_dump_json(exclude_none=True))],
        structured_content=body,
        is_error=True,
    )


class StageSpiritServer(MCPServer[None]):
    async def list_tools(self) -> list[MCPTool]:
        listing = await super().list_tools()
        for tool in listing:
            if tool.name != "runtime_status":
                tool.input_schema = _REQUEST_MODELS[tool.name].model_json_schema()
        return listing

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[None, Any] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        model = _REQUEST_MODELS.get(name)
        if model is None:
            raise MCPError(code=INVALID_PARAMS, message="工具不存在。")
        try:
            model.model_validate(arguments)
        except ValidationError as error:
            first = error.errors(include_input=False, include_url=False)[0]
            field = ".".join(str(part) for part in first["loc"]) or "arguments"
            return error_result(
                Error(
                    code="INVALID_ARGUMENT",
                    message="工具参数不符合字段类型或取值约束。",
                    retryable=False,
                    field=field,
                    action="按工具输入 Schema 修正参数。",
                )
            )
        try:
            result = await super().call_tool(name, arguments, context)
        except ToolError as error:
            cause: BaseException | None = error
            while cause is not None:
                if isinstance(cause, BusinessError):
                    return error_result(cause.error)
                cause = cause.__cause__
            raise
        if isinstance(result, CallToolResult):
            body: dict[str, Any] = result.structured_content or {}
            if name in ("settings_save", "settings_apply") and (
                body.get("application_state") == "failed" or body.get("state") == "failed"
            ):
                result.is_error = True
            if name != "runtime_status" and result.structured_content is not None:
                result.structured_content = _without_absent_optionals(result.structured_content)
                result.content = [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            result.structured_content, ensure_ascii=False, separators=(",", ":")
                        ),
                    )
                ]
        return result


def _without_absent_optionals(body: dict[str, Any]) -> dict[str, Any]:
    result = dict(body)
    for field in ("scope_id", "error"):
        if result.get(field) is None:
            result.pop(field, None)
    if result.get("error") is not None:
        result["error"] = Error.model_validate(result["error"]).model_dump(
            mode="json", exclude_none=True
        )
    return result


def create_server(runtime: RuntimeInstance) -> MCPServer[None]:
    active = runtime.configuration.snapshot()
    server = StageSpiritServer(
        "StageSpirit",
        version=__version__,
        log_level=active.log_level if active else "WARNING",
    )
    readonly = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    command = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    server.add_tool(
        runtime.snapshot,
        name="runtime_status",
        title="运行状态",
        description="读取当前运行配置、数据代际、实例身份和已启动模块的固定摘要。",
        annotations=readonly,
    )

    async def settings_get(
        section: SectionName, scope_id: ScopeId | None = None
    ) -> ConfigurationSection[RuntimeSettings]:
        return ConfigurationSection[RuntimeSettings].model_validate(
            await runtime.settings.get(section, scope_id)
        )

    async def settings_save(
        section: SectionName,
        data_generation: DataGeneration,
        expected_revision: Revision,
        changes: RuntimeSettingsChanges,
        scope_id: ScopeId | None = None,
    ) -> ConfigurationReceipt:
        return await runtime.settings.save(
            section=section,
            scope_id=scope_id,
            data_generation=data_generation,
            expected_revision=expected_revision,
            changes=changes.model_dump(exclude_unset=True),
        )

    async def settings_apply(
        section: SectionName,
        data_generation: DataGeneration,
        revision: Revision,
        idempotency_key: IdempotencyKey,
        scope_id: ScopeId | None = None,
    ) -> OperationReceipt:
        return await runtime.settings.apply(
            section=section,
            scope_id=scope_id,
            data_generation=data_generation,
            revision=revision,
            idempotency_key=idempotency_key,
        )

    async def operation_get(operation_id: str) -> OperationDetail:
        return await runtime.settings.operation_get(operation_id)

    server.add_tool(
        settings_get,
        title="读取配置",
        description="读取指定配置的保存值、活动值及修订；当前支持 runtime 分区。",
        annotations=readonly,
    )
    server.add_tool(
        settings_save,
        title="保存配置",
        description="按期望修订合并保存 runtime 配置并立即应用；失败时分别保留保存与活动状态。",
        annotations=command,
    )
    server.add_tool(
        settings_apply,
        title="应用已保存配置",
        description="以操作键再次应用当前保存修订；同键同请求返回原操作，旧修订不回滚。",
        annotations=command,
    )
    server.add_tool(
        operation_get,
        title="读取操作",
        description="读取单个配置应用操作的状态、效果及恢复结果。",
        annotations=readonly,
    )
    return server
