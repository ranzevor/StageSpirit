# MCP 接口参考

本文面向当前版本的 Agent 接入开发者，描述已经实现的 stdio MCP 接口。完整首版能力的设计见 MCP 契约设计。

[快速开始](../guides/quickstart.md) · [MCP 契约设计](../design/mcp-contract.md)

## 连接与发现

服务名称为 `StageSpirit`，通过标准输入输出传输。互通基线为 MCP `2025-11-25`，服务端和契约测试客户端使用锁定的 MCP Python SDK 2.3.0。初始化返回已安装的 StageSpirit 版本。

`tools/list` 返回下表工具及其输入、输出 Schema 和操作注解。当前目录包含五个固定工具，一页返回全部内容。`resources/list`、`resources/templates/list` 和 `prompts/list` 返回空目录。

| 工具 | 用途 | 操作性质 |
| --- | --- | --- |
| runtime_status | 当前实例与数据上下文 | 只读 |
| settings_get | 指定范围的保存值、活动值和修订 | 只读 |
| settings_save | 条件保存变更并触发应用 | 本地条件写入 |
| settings_apply | 按操作键再次应用当前保存修订 | 幂等操作 |
| operation_get | 单个配置应用操作的状态与恢复结果 | 只读 |

成功结果的 `structuredContent` 与文本 JSON 由同一对象生成，消费端选择一个正文处理。可选且无值的作用域和错误字段省略；`active_revision`、`active_values` 尚未激活时明确返回 `null`。

## 当前运行入口

`runtime_status` 输入为 `{}`，读取当前运行配置和实例摘要。工具为只读、幂等操作。

| 返回字段 | 含义 |
| --- | --- |
| profile_id | 当前运行配置 ID |
| data_generation | 该配置的持久数据代际，普通重启时保持 |
| instance_id | 本次启动的实例身份 |
| version | 当前安装的 StageSpirit 版本 |
| state | 当前实例状态，运行时为 running |
| process_id | 服务进程 ID |
| started_at | UTC 启动时间 |
| uptime_ms | 基于单调时钟计算的运行毫秒数 |
| capability_groups | 已启用的能力组，当前为 core |
| modules | 已装配模块的固定摘要，当前为 runtime、settings |

字段约束由运行状态 Schema 定义，并从运行时模型生成。

[运行状态 Schema](../../contracts/schemas/runtime-summary.schema.json) · [Python 连接示例](../../examples/mcp/runtime_status.py)

## 配置范围与值

当前提供 `section: "runtime"`，作用于整个 profile，`scope_id` 省略或为 `null`。其他分区及非空作用域返回 `INVALID_ARGUMENT`。

| 配置字段 | 类型与范围 | 默认值 | 生效方式 |
| --- | --- | --- | --- |
| log_level | DEBUG、INFO、WARNING、ERROR、CRITICAL | WARNING | 即时切换 StageSpirit 与 MCP 日志等级，日志继续写入标准错误 |

`settings_get` 输入包含 `section` 和可选 `scope_id`，输出包含 `values`、`active_values` 及配置回执字段。修订 0 表示初始默认配置。

`settings_save` 的输入如下。

| 字段 | 规则 |
| --- | --- |
| section、scope_id | 与读取的配置范围一致 |
| data_generation | 当前运行状态返回的数据代际 |
| expected_revision | 读取所得的 saved_revision，非负整数 |
| changes | 至少包含一个已支持字段的对象，按字段合并 |

未出现在 `changes` 中的字段保留；`log_level: null`、未知字段、空变更和布尔修订被拒绝。有效保存将修订递增一次，随后应用。并发条件检查与配置、操作记录在同一 SQLite 事务中提交。

## 配置回执与再次应用

| 返回字段 | 含义 |
| --- | --- |
| section、scope_id | 配置范围 |
| data_generation | 本次配置所属数据代际 |
| saved_revision | 已持久保存的修订 |
| active_revision | 当前进程已完成应用的修订，尚未激活时为 null |
| application_state | applied、applying 或 failed |
| apply_operation_id | 本次应用的操作身份 |
| error | 失败的具体原因和处理动作 |

`applied` 时保存修订和活动修订相等。应用失败保留新保存值与原活动值，保存回执同时返回 `isError: true`。保存事务失败返回结构化错误，调用方重新读取修订确认提交状态。

`settings_apply` 输入为相同 `section`、可选 `scope_id`、`data_generation`、`revision` 和 `idempotency_key`。修订必须等于当前保存修订；操作键为 1 至 128 个字符。结果遵循操作回执，包含 `operation_id`、`data_generation`、`state` 和可选 `error`。

同键同请求返回原操作；同键变更修订返回 `IDEMPOTENCY_CONFLICT`。已失败操作保持终态，重新尝试使用新键；完成记录持久保留。尚未完成的本地配置应用可沿原键恢复，执行代际递增。重启先清除上一进程的活动标记，再重新应用保存值；原待应用操作沿原身份恢复。

`operation_get` 输入为 `operation_id`，读取当前 profile 内该操作的执行代际、状态、效果和恢复状态。当前配置操作使用 `running`、`completed`、`failed` 三种状态。查询失败操作本身仍是一次成功查询。

[配置读取 Schema](../../contracts/schemas/settings-section.schema.json) · [配置回执](../../contracts/schemas/configuration-receipt.schema.json) · [操作详情](../../contracts/schemas/operation-detail.schema.json) · [保存与重启示例](../../examples/mcp/settings.py)

## 调用错误

| 情况 | 返回 |
| --- | --- |
| 未知协议方法 | JSON-RPC -32601 |
| 未知工具或方法参数结构无效 | JSON-RPC -32602 |
| 工具字段类型、值或范围无效 | isError 与 INVALID_ARGUMENT |
| 数据代际不匹配 | DATA_GENERATION_CHANGED，附当前代际 |
| 条件修订冲突 | REVISION_CONFLICT |
| 操作键对应不同修订 | IDEMPOTENCY_CONFLICT |
| 操作不属于当前 profile 或不存在 | NOT_FOUND |
| 配置应用失败 | CONFIGURATION_APPLY_FAILED，保留保存修订和原活动修订 |
| 数据库读写失败 | STORAGE_ERROR，重新读取配置确认提交结果 |
| 配置工作队列满 | QUEUE_FULL，本次请求尚未受理 |
| 服务关闭中 | SERVICE_CLOSING，本次请求尚未受理 |

业务错误包含 `code`、`message`、`retryable`，并按具体问题附 `field`、`action`、`operation_id` 或上下文。错误请求之后，连接继续处理有效调用。标准输出仅承载协议消息，运行诊断写入标准错误。
