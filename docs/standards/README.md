# 工程规范参考

本文面向项目维护者与技术评审，列出 StageSpirit 设计使用的 Ranzevor Standards 技术参考。规范集合版本为 0.2.0，单份规范版本与条款如下。

## 项目与文档

| 规范 | 版本 | 参考条款 | 对应设计用途 |
| --- | --- | --- | --- |
| STD-PG-003 需求设计与验收追溯规范 | 0.1.0 | PGT-01、PGT-02、PGT-03 | 需求身份、架构取舍、接口责任和需求到验收的关联 |
| STD-PG-004 仓库命名目录与内容归属规范 | 0.1.0 | PGR-02、PGR-03、PGR-04、PGR-06 | 目录分类、唯一正文、用途归属与实际引用迁移 |
| STD-PG-005 README品牌与徽章规范 | 0.1.0 | PGE-04、PGE-06 | 具名链接、目标章节、任务导航及设计阶段状态 |
| STD-PG-006 文档编制与国际化规范 | 0.1.0 | PGD-01、PGD-02、PGD-03、PGD-06 | 文档类型、中英文术语、任务步骤和链接示例同步 |

## 工程与技术

| 规范 | 版本 | 参考条款 | 对应设计用途 |
| --- | --- | --- | --- |
| STD-L3-001 通用工程规范 | 0.1.0 | 第一章、CE-01 | 根据当前用途、资产和副作用选择检查范围 |
| STD-L4-BACKEND-013 领域模型与服务边界技术规范 | 0.1.0 | 第四章、BE-004；第十三章、BE-013 | 业务生命周期划界、状态所有权和跨模块访问 |
| STD-L4-AI-AGENT-009 工具能力契约与 MCP 互操作技术规范 | 0.1.0 | §17 | tools/list、resources/list、prompts/list 的协议目录分页 |
| STD-L5-007 Python 技术适配规范 | 0.1.0 | STK-04 | asyncio 与线程任务的失败、取消和共享状态协调 |
| STD-L6-001 项目采用与实现验收接口规范 | 0.1.0 | ADP-01 | 选择正式采用对象时固定准确规范身份、版本与条款范围 |

## 查阅与维护

规范来源为 Ranzevor Standards 0.2.0。公开发行入口提供 Standards-v0.2.0-source.zip 和 Agent Skill 包，按发行包所含规范目录、条款登记与对应正文核对文档 ID、单份版本和条款所属章节。

[Standards 项目](https://github.com/ranzevor/Standards) · [0.2.0 发行](https://github.com/ranzevor/Standards/releases/tag/v0.2.0)

日常贡献按本项目贡献指南和工程约定执行。技术参考与正式项目采用分别维护，规范变更按项目实际决定更新其引用及受影响设计。

[贡献指南](../../CONTRIBUTING.md) · [工程约定](../development/engineering.md)

项目目录、业务结果、实现机制和测试预期各由对应正文维护。规范引用说明所用要求与设计的关系，文件版本和路径变化由 Git 管理。

[仓库结构](../development/repository.md) · [需求规格](../requirements/README.md) · [总体架构](../architecture/README.md) · [测试设计](../testing/README.md)
