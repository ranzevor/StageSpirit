# 工程规范采用

本文面向维护者和贡献者，定义 StageSpirit 采用的 Ranzevor Standards 范围及其工程入口。采用集合为 **0.2.0**，下表各正式规范的版本均为 **0.1.0**。规范身份和正文路径以该发行的 `registry/standards.json` 为准。

[标准项目](https://github.com/ranzevor/Standards) · [0.2.0 发行与正文](https://github.com/ranzevor/Standards/releases/tag/v0.2.0)

## 采用原则

全局治理、团队协作、通用工程和项目采用接口贯穿开发。项目治理要求覆盖定位、文档、Git、贡献、质量、安全、许可、发行和维护。领域及语言规范按实际工程对象和已确定的首版能力组合执行。

当前交付对象包括 Python 运行基础、stdio MCP、公开源码、依赖锁、文档、JSON Schema 和 GitHub 工作流。首版的配置、直播、语音、形象和展台已经纳入设计，实施与真实目标验收按各自交付阶段完成。

同一标准内的要求随其触发条件适用。多 Agent 委派、云部署、远程 MCP、支付、模型训练等要求分别在对应行为发生时使用。具体项目规则在下列工程正文中维护，执行授权与任务范围由当前任务确定。

## 通用与项目治理

| 标准 | 条款范围 | 项目落点 |
| --- | --- | --- |
| STD-L1-001 全局治理补充 | GG-01—08 | 规范版本、权责、授权与变更决定 |
| STD-L2-001 团队组织协作 | ORG-01—15，委派与并行条款按实际协作方式触发 | [贡献与审阅](../../CONTRIBUTING.md)、[执行约束](../../AGENTS.md) |
| STD-L3-001 通用工程 | CE-01—21 | [工程约定](../development/engineering.md)、[架构](../architecture/README.md)、[验收](../testing/README.md) |
| STD-L6-001 项目采用与实现验收接口 | ADP-01—07；ADP-08 用于规范采用示例 | 本页、[交付阶段](../development/delivery.md)、[验收场景](../testing/acceptance.md) |
| STD-PG-001 治理总则与职责接口 | PGF-01—06 | [文档职责](../README.md#文档职责)、[模块所有权](../architecture/README.md#模块与状态所有权) |
| STD-PG-002 项目立项定位与范围 | PGI-01—06 | [定位](../product/overview.md)、[范围](../product/scope.md) |
| STD-PG-003 需求设计与验收追溯 | PGT-01—06 | [需求规格](../requirements/README.md)、[验收场景](../testing/acceptance.md) |
| STD-PG-004 仓库命名目录与内容归属 | PGR-01—06 | [仓库结构](../development/repository.md) |
| STD-PG-005 README 品牌与徽章 | PGE-01—08 | [项目首页](../../README.md)、本地图标、任务导航与状态徽章 |
| STD-PG-006 文档编制与国际化 | PGD-01—08，译文要求在引入译文时适用 | [文档导航](../README.md)、[术语](../reference/glossary.md) |
| STD-PG-007 Git 工作区与本地操作 | PGW-01—10，stash 与 worktree 按实际操作触发 | 工作分支、差异审查、[提交检查](../development/engineering.md#提交与合并检查) |
| STD-PG-008 分支同步与冲突处理 | PGB-01—11，子模块与 LFS 按实际使用触发 | PR 基线、冲突处理与集成对象核对 |
| STD-PG-009 变更提案审查与合并 | PGC-01—06 | [贡献流程](../../CONTRIBUTING.md)、PR 和必需检查 |
| STD-PG-010 工作项里程碑与协作职责 | PGK-01—06 | Issues、PR、[交付计划](../development/delivery.md) |
| STD-PG-011 测试质量门禁与证据 | PGQ-01—06 | [测试分层](../testing/README.md)、CI 和实际测试结果 |
| STD-PG-012 依赖配置与供应链 | PGS-01—06 | [依赖和制品](../development/engineering.md#依赖和制品)、锁文件与工作流 |
| STD-PG-013 安全隐私与操作边界 | PGP-01—06 | [安全设计](../design/security.md)、[报告入口](../../SECURITY.md) |
| STD-PG-014 权属许可与第三方材料 | PGL-01—08 | [许可](../../LICENSE)、[材料来源](../../.github/scripts/NOTICE.md)、[贡献许可](../../CONTRIBUTING.md#内容来源与许可) |
| STD-PG-015 版本标签与发行 | PGV-01—06 | [版本与兼容](../development/compatibility.md)、[发行流程](../development/releasing.md) |
| STD-PG-016 部署配置迁移与回滚 | PGU-01—06，随安装更新和数据迁移触发 | [存储设计](../design/storage.md)、[更新方式](../development/compatibility.md#更新与数据兼容) |
| STD-PG-017 维护响应与兼容承诺 | PGM-01—06 | [维护与问题处理](../development/compatibility.md#维护与问题处理)、[安全报告](../../SECURITY.md) |
| STD-PG-018 弃用迁移归档与退役 | PGA-01—06，随对应生命周期动作触发 | [版本规则](../development/compatibility.md#版本规则)、[更正与恢复](../development/releasing.md#更正与恢复) |
| STD-PG-019 文件缓存构建物与证据生命周期 | PGX-01—06 | [目录职责](../development/repository.md)、[资源预算](../design/runtime.md)、Git 历史及 CI 记录 |
| STD-PG-020 规范采用例外与升级 | PGN-01—06 | 本页采用范围、规范升级的 PR 差异与对应验收 |

规范集合的目录与校验数据沿用上游发行。项目文件历史由 Git 维护，测试结果由执行命令与 CI 保存，需求和验收继续使用现有 REQ、ACC 标识关联。

## 当前实现与技术要求

| 标准 | 采用范围 | 实现与验证入口 |
| --- | --- | --- |
| STD-L5-007 Python | STK-01—06 | CPython、锁定环境、运行时模型、资源清理、异步协议、wheel 与 sdist 安装 |
| STD-L5-006 JavaScript / TypeScript | 当前 Node 工具的 STK-01—04、06；STK-05 随公开 JS 包交付触发 | CommonJS 检查脚本、输入验证、子进程与 Node 测试 |
| STD-L4-CLI-SDK-003 命令进程、配置与标准流 | CLI-PROC-01—05 | [快速开始](../guides/quickstart.md)、CLI 参数、UTF-8、标准流、退出与原子文件写入 |
| STD-L4-AI-AGENT-009 工具能力契约与 MCP 互操作 | §01—10、17—20、25、33、35—40；所选 2025 协议按 §11、30、41、43 核对兼容和取消 | [当前协议](../reference/mcp.md)、[完整契约设计](../design/mcp-contract.md)、stdio 契约测试 |
| STD-L4-CLOUD-001 CI 流程、Runner 与构建执行 | §01—08、11、13—14、19—28、31—38、43—48，按所用 GitHub 托管工作流适用 | `.github/workflows/`、最小权限、锁定工具、PR 与主分支检查 |
| STD-L4-OPEN-SOURCE-001 公共接口、发行安装与消费者兼容 | OSS-R01—05 | [兼容规则](../development/compatibility.md)、[发行安装](../development/releasing.md)、制品测试 |
| STD-L4-OPEN-SOURCE-002 开源公共生态基线 | M01—18，发行、签名与退役要求按实际动作触发 | 仓库身份、许可、贡献、依赖、安装、维护及公开接口 |
| STD-L4-OPEN-SOURCE-003 材料许可、贡献来源与可信构建 | OSS-B01—03；OSS-B04、05 随来源证明或 SBOM 格式采用触发 | [材料来源](../../.github/scripts/NOTICE.md)、锁定依赖、制品内容与许可检查 |
| STD-L4-OPEN-SOURCE-004 生态维护、漏洞响应与终止支持 | OSS-M01—04 | [维护方式](../development/compatibility.md)、[安全报告](../../SECURITY.md) |

## 首版业务设计

| 对象 | 标准与条款 | 设计入口及交付阶段 |
| --- | --- | --- |
| 领域边界与共享状态 | STD-L4-BACKEND-013，BE-001—022 | [架构与状态所有权](../architecture/README.md)、[内部接口](../architecture/interfaces.md)，D1—D5 |
| 外部连接、事件和恢复 | STD-L4-AUTOMATION-005、006；STD-L4-BACKEND-002、003、010、011 | [运行时](../design/runtime.md)、[存储](../design/storage.md)、[直播事件](../design/events.md)，D1、D4、D5 |
| 受控动作与执行权限 | STD-L4-AI-AGENT-004；STD-L4-SECURITY-001；STD-L4-CLOUD-013 | [安全](../design/security.md)、[角色控制](../design/avatar-performance.md)、[展台](../design/stage-obs.md)，D1、D3、D5 |
| 网络与实时媒体 | STD-L4-NETWORK-001—004 | [语音](../design/speech.md)、[形象](../design/avatar-performance.md)、[运行时预算](../design/runtime.md)，D2—D5 |
| 本地 Web、渲染与交互 | STD-L4-WEB-001—009、011；STD-L5-006 的浏览器与 TypeScript 条款 | [展台](../design/stage-obs.md)、[安全](../design/security.md)、[性能](../testing/performance.md)，D5 |

各规范内的适用要求落实到对应设计与 ACC 场景。提供方、浏览器、VTS、OBS 的具体版本、权限和性能观察在该模块实施时固定，与首版功能范围一同验收。

## 检查与变更

新增或修改能力时，核对本页涉及的标准与依赖，更新所属正文、Schema、正反例和验收入口。规范升级在 PR 中说明版本差异与受影响要求，维护者结合实际实现确认采用变更。

当前自动检查包含 Markdown 链接与章节、JSON 代码块、图标和徽章结构、Schema 正反例、生成契约、代码检查、stdio 互通、制品安装及提交元数据。语义、视觉、外部效果和兼容性按实际对象分别审查。

[检查命令](../development/engineering.md#开发环境与检查) · [测试设计](../testing/README.md) · [性能验收](../testing/performance.md)
