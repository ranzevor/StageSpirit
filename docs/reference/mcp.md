# MCP 接口参考

本文面向当前版本的 Agent 接入开发者，描述已经实现的 stdio MCP 接口。完整首版能力的设计见 MCP 契约设计。

[快速开始](../guides/quickstart.md) · [MCP 契约设计](../design/mcp-contract.md)

## 连接与发现

服务名称为 `StageSpirit`，通过标准输入输出传输。互通基线为 MCP `2025-11-25`，服务端和契约测试客户端使用锁定的 MCP Python SDK 2.3.0。初始化返回已安装的 StageSpirit 版本。

`tools/list` 返回 `runtime_status` 及其输入、输出 Schema 和只读注解。当前目录只有一个工具，一页返回全部内容。`resources/list`、`resources/templates/list` 和 `prompts/list` 返回空目录。

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
| modules | 已装配模块的固定摘要，当前为 runtime / ready |

成功结果的 `structuredContent` 与文本 JSON 由同一状态对象生成。字段约束由运行状态 Schema 定义，并从运行时模型生成。

[运行状态 Schema](../../contracts/schemas/runtime-summary.schema.json) · [Python 连接示例](../../examples/mcp/runtime_status.py)

## 协议错误

| 情况 | JSON-RPC 错误码 |
| --- | --- |
| 未知协议方法 | -32601 |
| 未知工具或方法参数结构无效 | -32602 |

错误请求之后，连接继续处理有效调用。标准输出仅承载协议消息，运行诊断写入标准错误。
