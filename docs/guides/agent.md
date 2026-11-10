# Agent 调用指南

本文面向连接当前 StageSpirit 开发版本的 Agent。安装及客户端配置见快速开始。

[快速开始](quickstart.md) · [当前 MCP 接口](../reference/mcp.md)

## 查询运行状态

1. 建立 stdio 连接并完成 MCP 初始化。
2. 调用 `tools/list`，取得当前进程实际公开的工具。目前返回 `runtime_status`。
3. 以空对象 `{}` 调用 `runtime_status`，读取 `structuredContent`。
4. 使用 `profile_id` 确认运行配置，使用 `data_generation` 识别持久数据集，使用 `instance_id` 区分本次启动。

成功结果同时包含等价的结构化内容与文本 JSON，选择一种处理即可。`state` 为 `running`，`modules` 为已装配模块的有限摘要。

## 处理连接和调用错误

连接启动失败时读取标准错误中的具体原因，按快速开始处理配置名称、实例占用或目录权限。MCP 未知工具返回 `-32602`，刷新实际工具目录后按发现结果调用。协议请求失败后可继续使用同一连接提交有效请求。

重复查询不修改配置。客户端断开后可重新启动服务，同一运行配置的数据代际保持。

[字段和错误](../reference/mcp.md) · [Python 连接示例](../../examples/mcp/runtime_status.py)

## 业务能力接入设计

后续的连接配置、语音与字幕、关键词动作、直播事件和展台流程按阶段交付。实现和集成开发者可按工作流设计核对前置、参数、结果及恢复，运行时按 `tools/list` 发现已交付能力。

[Agent 工作流设计](../design/agent-workflows.md) · [交付计划](../development/delivery.md)
