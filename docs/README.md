# StageSpirit 文档

本文面向使用者、Agent 接入开发者和项目维护者。文档以简体中文（zh-Hans）维护，分别提供当前版本用法、首版需求与实现设计。

## 使用当前版本

| 任务 | 入口 |
| --- | --- |
| 安装、配置 MCP 客户端和连接自检 | [快速开始](guides/quickstart.md) |
| 编写当前工具的调用流程 | [Agent 调用指南](guides/agent.md) |
| 查询实际协议和运行状态字段 | [MCP 接口参考](reference/mcp.md) |
| 确认运行环境、版本与更新方式 | [版本与兼容](development/compatibility.md) |

## 参与设计与开发

| 任务 | 入口 |
| --- | --- |
| 了解产品与首版范围 | [产品定位](product/overview.md)、[产品范围](product/scope.md) |
| 确认功能、责任与预期结果 | [需求规格](requirements/README.md) |
| 理解模块、状态所有权与跨模块协作 | [总体架构](architecture/README.md)、[内部接口设计](architecture/interfaces.md) |
| 实现运行时、直播、语音、形象和展台 | [专题设计](design/README.md) |
| 核对首版工具与 Agent 工作流 | [MCP 契约设计](design/mcp-contract.md)、[Agent 工作流设计](design/agent-workflows.md)、[共享契约](../contracts/README.md) |
| 查阅统一术语 | [术语表](reference/glossary.md) |
| 理解架构选择与取舍 | [架构决策记录](adr/README.md) |
| 建立开发环境、维护仓库和准备发行 | [开发文档](development/README.md) |
| 编写和执行验收 | [测试设计](testing/README.md)、[验收场景](testing/acceptance.md) |
| 确认采用的工程规范 | [规范采用](standards/README.md) |

## 文档职责

产品文档说明目标读者、场景和能力范围。需求定义结果与验收义务，架构和专题设计定义机制与责任。当前接口参考描述已经交付的行为，指南给出可执行步骤。ADR 保存技术选择，测试文档定义初态、输入和预期。

字段结构由 `contracts/` 维护。已经实现的输出从运行时模型生成，其余契约随对应模块接入。各正文通过链接引用唯一维护源，目录和文件历史由 Git 管理。

[仓库结构与文档维护](development/repository.md) · [贡献指南](../CONTRIBUTING.md)
