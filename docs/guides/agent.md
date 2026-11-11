# Agent 调用指南

本文面向连接当前 StageSpirit 开发版本的 Agent。安装及客户端配置见快速开始。

[快速开始](quickstart.md) · [当前 MCP 接口](../reference/mcp.md)

## 查询运行状态

1. 建立 stdio 连接并完成 MCP 初始化。
2. 调用 `tools/list`，取得当前进程实际公开的工具。目前包含运行状态、配置读取、保存、应用及单条操作查询。
3. 以空对象 `{}` 调用 `runtime_status`，读取 `structuredContent`。
4. 使用 `profile_id` 确认运行配置，使用 `data_generation` 识别持久数据集，使用 `instance_id` 区分本次启动。

成功结果同时包含等价的结构化内容与文本 JSON，选择一种处理即可。`state` 为 `running`，`modules` 为已装配模块的有限摘要。

## 保存和应用配置

1. 用 `settings_get` 读取 `section: "runtime"`，取得保存值、活动值和 `saved_revision`。
2. 用 `settings_save` 提交相同分区、当前 `data_generation`、读取所得的 `expected_revision`，以及 `changes`，例如 `{"log_level":"ERROR"}`。当前分区作用于整个 profile，省略 `scope_id`。
3. 读取返回的 `saved_revision`、`active_revision` 和 `application_state`。两修订相等且状态为 `applied` 时，本次保存值已在当前进程生效。
4. 保存值已经提交但应用失败时，保留回执中的 `apply_operation_id`。通过 `operation_get` 读取具体状态，再用 `settings_apply` 对当前保存修订重新应用，并提供一个新的 `idempotency_key`。

`changes` 按字段合并，省略字段保持原值。当前支持 `log_level`；空变更、未知字段和不符合字段类型的 null 被拒绝。日志等级更改不改变协议输出通道。

同一操作键重试相同应用请求返回原操作；终态失败后的再次执行使用新键。修订冲突时重新读取配置并核对已保存内容，不能把更早修订当成回滚请求。数据代际变化时先刷新运行状态与配置，再组织新的变更。

重启会恢复保存值，新的进程重新确认活动修订。原待应用操作沿原身份继续，旧实例或旧执行代际的完成结果不会覆盖新配置。

[配置字段与错误](../reference/mcp.md#配置范围与值) · [隔离运行示例](../../examples/mcp/settings.py)

## 处理连接和调用错误

连接启动失败时读取标准错误中的具体原因，按快速开始处理配置名称、实例占用或目录权限。MCP 未知工具返回 `-32602`，刷新实际工具目录后按发现结果调用。协议请求失败后可继续使用同一连接提交有效请求。

重复查询不修改配置。客户端断开后可重新启动服务，同一运行配置的数据代际保持。

[字段和错误](../reference/mcp.md) · [Python 连接示例](../../examples/mcp/runtime_status.py)

## 业务能力接入设计

后续的连接配置、语音与字幕、关键词动作、直播事件和展台流程按阶段交付。实现和集成开发者可按工作流设计核对前置、参数、结果及恢复，运行时按 `tools/list` 发现已交付能力。

[Agent 工作流设计](../design/agent-workflows.md) · [交付计划](../development/delivery.md)
