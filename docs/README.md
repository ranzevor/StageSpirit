# StageSpirit 文档

本文是文档导航，面向产品使用者、Agent 接入开发者和项目维护者。文档以中文（zh-Hans）编写，当前用于项目设计与后续实现。

## 按任务阅读

| 读者任务 | 入口 |
| --- | --- |
| 了解产品与首版范围 | [产品定位](product/overview.md)、[产品范围](product/scope.md) |
| 确认功能、责任与预期结果 | [需求规格](requirements/README.md) |
| 理解模块、状态所有权与跨模块协作 | [总体架构](architecture/README.md)、[内部接口设计](architecture/interfaces.md) |
| 实现运行时、直播、语音、形象和展台 | [专题设计](design/README.md) |
| 查询协议、字段与术语 | [接口与术语参考](reference/README.md)、[共享契约](../contracts/README.md) |
| 开发 Agent 调用流程 | [调用指南](guides/README.md) |
| 理解架构选择与取舍 | [架构决策记录](adr/README.md) |
| 维护仓库并安排实现 | [开发文档](development/README.md) |
| 编写和执行验收 | [测试设计](testing/README.md)、[验收场景](testing/acceptance.md) |
| 查阅所引用的工程规范 | [规范参考](standards/README.md) |

## 文档职责

产品文档说明目标读者、使用场景和能力范围。需求规格定义结果与验收义务，架构和专题设计说明实现机制及责任接口。参考文档集中描述术语、协议和字段，指南按任务说明前置、步骤、结果及恢复。ADR 记录重要技术选择，测试文档维护输入、观察点与预期。

功能要求由需求规格承载，字段结构由 contracts 中的定义承载。各类文档通过链接引用对应正文，修改时同步受影响的设计、示例、调用说明和验收场景。目录维护方式见仓库结构。

[仓库结构与文档维护](development/repository.md) · [工程规范参考](standards/README.md)
