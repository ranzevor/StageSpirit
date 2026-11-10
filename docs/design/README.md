# 专题设计

本文面向功能实现和技术评审，按业务责任组织流程、状态、失败处理与恢复机制。模块关系及通用协作接口由架构文档定义，各专题展开所属机制。

[总体架构](../architecture/README.md) · [内部接口设计](../architecture/interfaces.md) · [需求规格](../requirements/README.md)

| 专题 | 负责内容 |
| --- | --- |
| [MCP 契约](mcp-contract.md) | 工具分组、发现、分页、回执与通知 |
| [Agent 工作流](agent-workflows.md) | 各业务任务的前置、调用顺序与恢复 |
| [运行时与操作生命周期](runtime.md) | 启动关闭、长操作、取消、幂等、代际和队列 |
| [数据、配置与恢复](storage.md) | 状态归属、配置事务、持久化、迁移与恢复 |
| [直播事件与可靠消费](events.md) | 事件字段、持久历史、水位、规则与动作身份 |
| [语音与字幕](speech.md) | 提供方、音色、文本投影、播放与转写 |
| [虚拟形象与语义表演](avatar-performance.md) | 模型发现、输入映射、表情、嘴型和控制仲裁 |
| [展台与 OBS 应用](stage-obs.md) | 编辑与 Web 同步、层序、预检、输出生命周期及补偿 |
| [访问与资源边界](security.md) | 凭据、文件范围、输出访问和业务写入权限 |

协议分页、错误码及通知格式见 MCP 契约设计，数据结构和请求示例见共享契约。

[MCP 契约设计](../design/mcp-contract.md) · [工具与数据契约](../../contracts/README.md)
