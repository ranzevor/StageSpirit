# 实施与交付顺序

本文是面向实施与验收的阶段计划，按首版使用链路安排成果、依赖和退出条件。

按完整使用链路分批交付，每批形成可独立运行、验证和回退的能力。接口责任先固定，提供方逐个接入，已有通过结果按变更影响复用。

| 阶段 | 成果与依赖 | 核心退出条件 |
| --- | --- | --- |
| D1 独立运行基础 | 安装入口、配置与数据代际、版本化查询、凭据、本地 Web 会话、操作账、提供方发现和 MCP 核心工具 | 干净环境安装，配置重启恢复，旧代际与跨站请求被拒绝，实际客户端可发现和调用 |
| D2 语音链路 | 基于 D1；一个 OpenAI 兼容目标的合成、播放、转写、音色目录、缓存隔离及字幕投影 | 真实音频、播放时钟与正文对齐来源分别可观察，标签保留用于发声、字幕按规则清理 |
| D3 角色表达 | 基于 D1、D2；模型发现、表情、热键、嘴型、独立语义配置及参数仲裁 | 不同映射模型、并发动作、模型重载和在播配置切换通过验收 |
| D4 直播互动 | 基于 D1 与动作目标接口；三平台事件、持久历史、通知、规则及动作分发 | SC／礼物信息完整，消费恢复与重复消息不重复产生逻辑动作 |
| D5 展台播出 | 基于 D1、D2 的播放事件及 D3 的模型绑定；完整编辑、背景与前景平面、只读输出、OBS 准备、应用与补偿 | 快照续流、底层背景与捕获框饰、共享来源保护、输出结果查询、陈旧预检及恢复冲突分别通过 |
| D6 渠道与发行 | 汇合 D1 至 D5；其余 TTS 提供方、完整支持矩阵、安装包与用户指南 | 首版范围全部覆盖，安装制品和每个声明支持的适配器完成相应验收 |

D1 固定 PlaybackEvent、PlaybackAlignment、CollectionSnapshot、AvatarControl、ConfigurationParticipant 和 BroadcastControl 的最小接口。D2 的字幕投影可单独验证，D5 再验证实际 OBS 展示。D6 完成[首版范围](../product/scope.md)内的全部渠道，早期可用链路不缩减稳定版范围。[性能需求](../requirements/README.md#req-perf-001)随各阶段链路验收，统一场景入口为 [ACC-PERF-001](../testing/acceptance.md#acc-perf-001)。

## 当前交付

当前提供 D1 的安装与运行基础，以及 SQLite 配置持久化。settings_get、settings_save、settings_apply 已接入 runtime.log_level，operation_get 可读取配置应用操作；保存与活动修订分离，支持条件写入、原操作重试和重启恢复。

D1 的其他配置分区、导入导出与数据恢复、分页、凭据、完整操作管理和提供方发现继续按本阶段退出条件交付。

[当前使用入口](../guides/quickstart.md) · [当前接口](../reference/mcp.md)

## 阶段与需求

| 阶段 | 对应需求 |
| --- | --- |
| D1 | [独立安装](../requirements/README.md#req-ind-001)、[生命周期](../requirements/README.md#req-run-001)、[操作恢复](../requirements/README.md#req-run-002)、[配置恢复](../requirements/README.md#req-cfg-001)、[导入与数据恢复](../requirements/README.md#req-cfg-002)、[MCP 接入](../requirements/README.md#req-mcp-001)、[分页](../requirements/README.md#req-mcp-002)、[访问范围](../requirements/README.md#req-sec-001)、[独立制品与编码](../requirements/README.md#req-eng-001) |
| D2 | [TTS 能力](../requirements/README.md#req-tts-001)、[音色发现](../requirements/README.md#req-tts-002)、[文本投影](../requirements/README.md#req-tts-003)、[播放](../requirements/README.md#req-tts-004)、[转写](../requirements/README.md#req-stt-001) |
| D3 | [模型控制](../requirements/README.md#req-ava-001)、[表情](../requirements/README.md#req-ava-002)、[嘴型](../requirements/README.md#req-lip-001)、[语义配置](../requirements/README.md#req-sem-001)、[参数仲裁](../requirements/README.md#req-sem-002) |
| D4 | [事件字段](../requirements/README.md#req-evt-001)、[历史与分发](../requirements/README.md#req-evt-002)、[过滤与触发](../requirements/README.md#req-evt-003) |
| D5 | [OBS 控制](../requirements/README.md#req-obs-001)、[展台编辑与同步](../requirements/README.md#req-stg-001)、[应用核对](../requirements/README.md#req-stg-002)、[补偿与资源保护](../requirements/README.md#req-stg-003) |
| D6 | 完成上述需求在全部首版渠道与安装制品中的适用场景 |

## 阶段与性能验收

| 阶段 | 关联验收场景 | 性能退出内容 |
| --- | --- | --- |
| D1 | [ACC-RUN-001](../testing/acceptance.md#acc-run-001)、[ACC-RUN-003](../testing/acceptance.md#acc-run-003)、[ACC-CFG-003](../testing/acceptance.md#acc-cfg-003)、[ACC-MCP-002](../testing/acceptance.md#acc-mcp-002) | [核心查询、分页、启动与数据恢复](../testing/performance.md#阶段覆盖)，并建立本阶段稳定性基线 |
| D2 | [ACC-TTS-002](../testing/acceptance.md#acc-tts-002)、[ACC-TTS-004](../testing/acceptance.md#acc-tts-004)、[ACC-TTS-005](../testing/acceptance.md#acc-tts-005)、[ACC-STT-001](../testing/acceptance.md#acc-stt-001) | [音色分页、播放启动、首音与字幕](../testing/performance.md#阶段覆盖)，加入语音和字幕混合负载 |
| D3 | [ACC-LIP-001](../testing/acceptance.md#acc-lip-001)、[ACC-SEM-001](../testing/acceptance.md#acc-sem-001)、[ACC-SEM-002](../testing/acceptance.md#acc-sem-002)、[ACC-SEM-003](../testing/acceptance.md#acc-sem-003) | [嘴型、cue 调度与映射激活](../testing/performance.md#阶段覆盖)，核对仲裁、租约和在播更新 |
| D4 | [ACC-EVT-001](../testing/acceptance.md#acc-evt-001)、[ACC-EVT-002](../testing/acceptance.md#acc-evt-002)、[ACC-EVT-004](../testing/acceptance.md#acc-evt-004)、[ACC-EVT-005](../testing/acceptance.md#acc-evt-005) | [事件保存、通知、百万历史与突发恢复](../testing/performance.md#阶段覆盖) |
| D5 | [ACC-STG-002](../testing/acceptance.md#acc-stg-002)、[ACC-STG-003](../testing/acceptance.md#acc-stg-003)、[ACC-STG-005](../testing/acceptance.md#acc-stg-005)、[ACC-STG-006](../testing/acceptance.md#acc-stg-006) | [展台帧耗时、OBS 字幕与 Web 重连](../testing/performance.md#阶段覆盖)，执行捕获与 Web 平面的完整组合 |
| D6 | [ACC-TTS-001](../testing/acceptance.md#acc-tts-001)、[ACC-STT-001](../testing/acceptance.md#acc-stt-001)、[ACC-ENG-001](../testing/acceptance.md#acc-eng-001)、[ACC-ENG-002](../testing/acceptance.md#acc-eng-002)及各模块适用场景 | [安装制品与全部首版渠道的完整负载](../testing/performance.md#阶段覆盖)，执行 30 分钟基准和 2 小时混合压力 |

## 分批实施规则

每批只包含一个可说明的业务行为或一致的基础改动，先明确输入、结果、故障分支与回退对象。相关源码、契约、示例和使用说明一同更新。

外部系统验证通过 MCP 客户端、HTTP/WebSocket 和目标服务 API 完成。OBS 使用隔离场景和来源，读回节目场景、来源属性及恢复结果。技术路径按[工程规范](engineering.md)组织。

## 需要在对应阶段固定的参数

| 参数 | 固定时点 | 判据 |
| --- | --- | --- |
| Python、MCP SDK 与客户端版本 | D1 构建输入建立时 | 能从锁文件重建并实际互通 |
| 提供方 SDK 与前端工具链 | 各适配器接入及 D5 前端构建时 | 提供方依赖、Node.js 和前端锁文件分别对应实际制品 |
| 许可和复用材料 | 引入材料及准备发行时 | 来源与适用许可明确 |
| 队列容量、资源预算及计划有效期 | speech 待播默认 64、合成并发默认 2 由本设计固定，D2 验收；其他预算在 D1 至 D3 所属模块建立时固定 | 采用[运行时预算](../design/runtime.md#队列)，按[过载与稳定性](../testing/performance.md#过载与稳定性)验证拒绝、回收和恢复 |
| 可变列表版本、快照租约及回收预算 | D1 查询基础建立时 | 更新、删除、过期、资源超限及数据恢复后的读取结果可区分 |
| 性能参考负载与数值目标 | 本设计固定，D1 至 D6 按所属链路退出时实测 | 使用[性能验收规格](../testing/performance.md)，逐项比较分位数、完整性和资源增长 |
| 提供方、VTS、OBS 版本矩阵 | 对应适配器验收时 | 指定目标的实际行为 |
| 模型输入、表情覆盖及混合策略 | D3 模型配置时 | 来自模型能力和明确配置 |
| 保留与备份策略 | D1 存储配置时 | 默认持久保存；清理受显式策略及引用保护，备份由明确操作或已启用策略触发 |

## 阶段退出

按[需求](../requirements/README.md)关联的[验收场景](../testing/acceptance.md)及[性能规格](../testing/performance.md)检查本阶段成果。测试结果对应实际实现、目标版本、输入与观察。安装检查覆盖实际制品，适配器验收覆盖其声明支持的目标版本。

阶段退出以对应链路的可观察结果判定。变更触发相关回归，未受影响的通过分支沿用原结果；明确要求复核时按指定范围执行。
