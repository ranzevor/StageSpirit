# 需求规格

本文面向需求确认、设计和测试，规定首个稳定版本的责任主体、触发条件与可观察结果。下列需求均属于首版必需范围，来源为[产品范围](../product/scope.md)。术语见[术语表](../reference/glossary.md)。

需求保留稳定的 REQ 标识。每项关联负责设计和验收场景，具体测试输入、步骤及预期在[验收设计](../testing/acceptance.md)维护。

<a id="req-ind-001"></a>

## REQ-IND-001 独立构建、安装、配置与外部资源身份

责任主体为制品与安装维护者，运行时由 bootstrap 装配各模块。

在独立目录安装和启动时，项目分别维护构建、安装包、配置格式、应用数据、插件认证及受管资源身份。运行数据按运行配置隔离。

从源码目录以外完成安装后，入口、包内资源和配置仍能使用。显式绑定的既有外部对象保留原归属。

[工程约定](../development/engineering.md) · [ACC-IND-001](../testing/acceptance.md#acc-ind-001)

<a id="req-run-001"></a>

## REQ-RUN-001 受管理的生命周期、单配置实例和局部失败隔离

责任模块为 `runtime`。

启动、连接、关闭及局部服务失败时，runtime 管理实例锁、连接和后台任务，业务模块维护自己的状态与完成判据。一个运行配置对应一个控制实例。

单个连接失败只影响其依赖能力。关闭流程停止受理、协调取消并释放资源，模块间通过公开接口协作。

[运行时设计](../design/runtime.md) · [ACC-RUN-001](../testing/acceptance.md#acc-run-001)、[ACC-RUN-002](../testing/acceptance.md#acc-run-002)、[ACC-ARCH-001](../testing/acceptance.md#acc-arch-001)

<a id="req-run-002"></a>

## REQ-RUN-002 长操作状态、取消、幂等和迟到回调处理

责任模块为 `runtime`。

受理长操作、收到重复请求、取消或迟到回调时，runtime 按操作身份、幂等键和执行代际协调状态。

相同逻辑请求取得同一操作，不同输入复用同一键返回冲突。查询结果分别表达受理、完成、已发生效果和恢复状态，取消与完成竞争以实际效果判定。所有变更请求携带当前数据代际，旧代际请求返回 DATA_GENERATION_CHANGED 及当前代际。已受理操作仍可查询或按原身份恢复，恢复数据库后不作为新动作重放。

[运行时设计](../design/runtime.md) · [ACC-RUN-003](../testing/acceptance.md#acc-run-003)、[ACC-RUN-004](../testing/acceptance.md#acc-run-004)

<a id="req-cfg-001"></a>

## REQ-CFG-001 所有服务配置保存、重启恢复和运行生效状态分离

责任模块为 `settings`。

保存任一服务连接、模型配置、语义规则或展台设置时，settings 协调所属模块校验并持久提交配置修订，再由模块应用。

重启恢复已保存配置。保存修订与活动修订分别返回，激活失败保留具体错误和可再次应用的修订，旧连接回调不能把新配置标成生效。

[数据与配置设计](../design/storage.md) · [ACC-CFG-001](../testing/acceptance.md#acc-cfg-001)、[ACC-CFG-002](../testing/acceptance.md#acc-cfg-002)、[ACC-CFG-004](../testing/acceptance.md#acc-cfg-004)

<a id="req-cfg-002"></a>

## REQ-CFG-002 版本化导入导出、数据库迁移和备份恢复

责任模块为 `settings`。

导入、导出、升级或恢复配置数据时，settings 按版本化格式、期望修订和明确的合并、替换或删除语义处理。

非法导入在修改前被拒绝，合法导入按事务提交。迁移失败保留原有数据，数据库和被引用媒体能够在明确的备份操作或已启用策略下完成一致备份与恢复，凭据按系统能力重新绑定。运行配置持久保存 data_generation，恢复数据库时生成新代际并与数据库切换状态一并保存。修订和事件接收序列仅在同一数据代际内比较，切换中断后能够恢复到一致的数据库与代际。

[数据与配置设计](../design/storage.md) · [ACC-CFG-003](../testing/acceptance.md#acc-cfg-003)、[ACC-CFG-004](../testing/acceptance.md#acc-cfg-004)、[ACC-CFG-005](../testing/acceptance.md#acc-cfg-005)

<a id="req-evt-001"></a>

## REQ-EVT-001 三平台归一化及SC、礼物、会员信息完整

责任模块为 `live_events`。

接收 Bilibili、YouTube 和 Twitch 的聊天、SC、礼物或会员事件时，live_events 将平台数据转换为统一业务事件。

事件保留完整正文、UID、昵称、等级、会员、礼物数量及价值单位。金额、平台积分与 Bits 保留原有业务区别，合法的 0 和 false 能被传递。

[直播事件设计](../design/events.md) · [ACC-EVT-001](../testing/acceptance.md#acc-evt-001)、[ACC-EVT-005](../testing/acceptance.md#acc-evt-005)

<a id="req-evt-002"></a>

## REQ-EVT-002 事件持久化历史、分发、断线补拉和去重

责任模块为 `live_events`。

接收事件、分发通知、查询历史或从断线和进程中断恢复时，live_events 先持久保存，再分别推进接收及消费者水位。

礼物与其他事件均可查询本地历史。相同上游身份去重，各消费者按数据代际和本地稳定序列独立恢复，游标及 after_sequence 续读携带同一代际。上游可补拉时按能力补拉，缺少上游重放能力的窗口记录接收间断。显式保留策略已删除所请求的历史时，返回 HISTORY_GAP 及最早可读序列，由消费者明确选择新的起点。

[直播事件设计](../design/events.md) · [ACC-EVT-002](../testing/acceptance.md#acc-evt-002)、[ACC-EVT-004](../testing/acceptance.md#acc-evt-004)、[ACC-EVT-005](../testing/acceptance.md#acc-evt-005)

<a id="req-evt-003"></a>

## REQ-EVT-003 过滤、替换、关键词触发与冷却

责任模块为 `live_events`。

匹配过滤、替换和关键词触发规则时，live_events 区分展示变化和动作决定，保留原始业务正文。

首次决定动作时固定事件、规则修订和动作身份，重投与自动恢复复用该决定。并发请求共享冷却判据，规则失败只影响相应规则处理。

[直播事件设计](../design/events.md) · [ACC-EVT-003](../testing/acceptance.md#acc-evt-003)、[ACC-EVT-004](../testing/acceptance.md#acc-evt-004)

<a id="req-tts-001"></a>

## REQ-TTS-001 多提供方、能力声明及参数校验

责任模块为 `speech`。

选择语音提供方并提交合成参数时，speech 按该提供方声明的模型、音色、语言和控制能力校验输入。

首版覆盖产品范围内的六类 TTS 提供方，OpenAI 兼容适配包含 VoiceStudio。未支持的参数返回具体能力错误，单个可选提供方缺失只影响该适配器。

[语音与字幕设计](../design/speech.md) · [ACC-TTS-001](../testing/acceptance.md#acc-tts-001)

<a id="req-tts-002"></a>

## REQ-TTS-002 音色发现、来源标记、筛选与分页

责任模块为 `speech`。

查询音色或读取音色详情时，speech 返回稳定音色身份、名称、提供方、语言、目录来源以及必要模型和后端选项。

目录支持筛选、刷新和分页。服务发现、固定目录、手工配置与当前配置值分别标识，发现失败、无目录接口及空目录在列表元数据中分别表达，空列表仍能查询目录状态。

[语音与字幕设计](../design/speech.md) · [ACC-TTS-002](../testing/acceptance.md#acc-tts-002)

<a id="req-tts-003"></a>

## REQ-TTS-003 口语风格、发声标签保留、中文提示清理、独立字幕投影与逐字模式

责任模块为 `speech`。

准备说话、逐字朗读、字幕或关键词匹配正文时，各所属模块按文本用途生成独立视图。

spoken 模式过滤已识别的中文括号表演提示并保留正常说明，verbatim 保留原文。发声标签传给 TTS，字幕清除全部 ASCII 方括号块及内容，覆盖嵌套、多行、未闭合和纯标签输入。清理后再进行字幕分句。

[语音与字幕设计](../design/speech.md) · [ACC-TTS-003](../testing/acceptance.md#acc-tts-003)、[ACC-TTS-005](../testing/acceptance.md#acc-tts-005)

<a id="req-tts-004"></a>

## REQ-TTS-004 合成文件、实际音频播放、队列和停止

责任模块为 `speech`。

提交合成、播放、排队、打断或停止时，speech 管理音频资源、实际播放和操作状态。

仅合成返回音频文件资源，播放事实按实际设备生命周期和时钟产生。priority 为 0 至 9、默认 5，数值大者先播放，同级按持久入队序号先进先出；取得播放权后保持本次选择。interrupt_current 显式停止当前播放并保留下一播放权，同槽位只有一个未完成切换，确认旧播放停止及控制释放后启动替代任务。默认待播容量 64、合成并发 2，满额在受理前拒绝。停止只作用于指定操作，其余任务继续执行。

[语音与字幕设计](../design/speech.md) · [ACC-TTS-004](../testing/acceptance.md#acc-tts-004)、[ACC-TTS-005](../testing/acceptance.md#acc-tts-005)

<a id="req-stt-001"></a>

## REQ-STT-001 OpenAI兼容转写及VoiceStudio适配

责任模块为 `transcription`。

提交授权音频资源进行转写时，transcription 使用配置的 OpenAI 兼容音频转写接口，包含 VoiceStudio 目标。

输入通过格式、大小、时长和解码校验，结果保留完整文本及上游实际提供的分段和时间信息。超时和取消按原操作身份查询与恢复。

[语音与字幕设计](../design/speech.md) · [ACC-STT-001](../testing/acceptance.md#acc-stt-001)

<a id="req-ava-001"></a>

## REQ-AVA-001 模型、道具、移动、参数和当前代际热键

责任模块为 `avatar`。

发现模型或执行道具、移动、参数及热键操作时，avatar 使用当前模型能力、输入范围和模型代际。

model_id 是运行配置内唯一的模型身份，绑定 VTS connection_id 与 provider_model_id。同一原生模型通过不同连接接入时，模型配置与代际相互隔离。模型重载后重新发现热键 ID，逻辑热键绑定解析到当前目录，重名返回歧义。追踪输入与模型输出分别建模，通过真实映射取得控制目标。

[形象与语义表演设计](../design/avatar-performance.md) · [ACC-AVA-001](../testing/acceptance.md#acc-ava-001)

<a id="req-ava-002"></a>

## REQ-AVA-002 通用表情互斥、叠加及切换回读

责任模块为 `avatar`。

切换表情及组合时，avatar 根据配置的互斥组、叠加关系和嘴部覆盖策略计算变化、执行并回读。

同组并发切换串行处理，冲突按策略消除，组外有效表情保留。部分执行失败后回读实际表情状态，完成状态与当前 VTS 观察一致，规则适用于通过能力发现和显式绑定接入的模型。

[形象与语义表演设计](../design/avatar-performance.md) · [ACC-AVA-002](../testing/acceptance.md#acc-ava-002)

<a id="req-lip-001"></a>

## REQ-LIP-001 按实际音频和映射驱动嘴型并正确释放

责任模块为 `avatar`。

实际音频播放产生包络时，avatar 按模型输入映射驱动允许的嘴部通道，映射无需与输出参数同名。

嘴型与当前表情覆盖策略协调，未知作用范围动作期间暂停相关自动嘴型。静音、结束、中断、取消和断线释放本次播放持有的控制，旧代际回调不能继续修改当前模型。

[形象与语义表演设计](../design/avatar-performance.md) · [ACC-LIP-001](../testing/acceptance.md#acc-lip-001)

<a id="req-sem-001"></a>

## REQ-SEM-001 独立语义配置持久化、关键词匹配及实时生效

责任模块为 `performance`。

通过独立语义配置工具保存关键词、排除词、标签和参数映射时，performance 持久化修订并切换活动匹配配置。

普通 TTS 请求只需提供语音内容。排队语音使用开始播放时的活动修订，在播更新从当前调度位置之后重建未来片段，已触发关键词不重复执行。运行摘要可查询当前修订、调度位置、暂停原因和时间来源，分别表达实际播放时钟与正文对齐来源。有 PCM 而无正文时间戳时使用文本估算对齐。延迟收到开始事件的消费者沿用原开始时刻与时钟域。

[形象与语义表演设计](../design/avatar-performance.md) · [ACC-SEM-001](../testing/acceptance.md#acc-sem-001)、[ACC-SEM-003](../testing/acceptance.md#acc-sem-003)、[ACC-SEM-004](../testing/acceptance.md#acc-sem-004)

<a id="req-sem-002"></a>

## REQ-SEM-002 按最终参数仲裁动作、表情、嘴型和语义冲突

责任模块为 `avatar`。

手动控制、表情、动作、嘴型与语义同时请求参数写入时，avatar 沿输入映射将竞争归并到最终输出参数并统一仲裁。

默认顺序为手动参数控制、明确动作与表情、允许的嘴型、语义细节，表情配置明确允许的嘴部覆盖继续生效。每个意图的完整输出集合整组授予或跳过，同级明确参数控制保留先持有者，后到请求返回 PARAMETER_BUSY；互斥表情组切换仍串行处理。同一意图中不同输入解析到重叠输出时返回 PARAMETER_CONFLICT。语义在固定调度批次内按 priority 降序、mapping_id、model_id、intent_id 升序仲裁，跨批次保留已跳过决定，抢占撤销旧意图的完整租约，无法安全停止的原生动作保持占用。写入及释放检查所有者、代际和当前 lease_id，部分外部写入回读实际效果并沿原操作恢复。未知作用范围动作期间暂停相关自动嘴型与语义，恢复后只调度仍有效的未来意图。

[形象与语义表演设计](../design/avatar-performance.md) · [ACC-SEM-002](../testing/acceptance.md#acc-sem-002)、[ACC-ARCH-001](../testing/acceptance.md#acc-arch-001)、[ACC-SEM-003](../testing/acceptance.md#acc-sem-003)

<a id="req-obs-001"></a>

## REQ-OBS-001 OBS直接控制及并发请求正确关联

责任模块为 `broadcast`。

直接控制 OBS 或由展台应用调用 OBS 时，broadcast 统一管理连接、请求关联及目标资源写入。

并发响应对应原请求，全局来源设置、场景项属性和场景排序分别协调写入并回读。跨场景共享来源的操作保护其他引用。场景、场景项、可见性、文字、滤镜、推流、录制和状态查询按各自实际效果回读。

[展台与 OBS 设计](../design/stage-obs.md) · [ACC-OBS-001](../testing/acceptance.md#acc-obs-001)、[ACC-OBS-002](../testing/acceptance.md#acc-obs-002)、[ACC-STG-004](../testing/acceptance.md#acc-stg-004)

<a id="req-stg-001"></a>

## REQ-STG-001 布局、组件、媒体、预设及撤销重做

责任模块为 `stage`。

编辑展台布局、皮肤、预设、组件或媒体时，stage 维护项目修订及编辑历史。

弹幕、字幕、白板、公告、模型和捕获组件分别保持业务状态。MCP 与 Web 使用同一应用服务和修订，提交后的变更可由 Web 订阅及带水位快照连续读取。较早回执和迟到读取不覆盖较新的修订或组件状态序列，字幕状态在同一数据代际内递增。编辑批次全部提交或拒绝，撤销重做保持有效历史，新编辑正确处理重做分支。

[展台与 OBS 设计](../design/stage-obs.md) · [ACC-STG-001](../testing/acceptance.md#acc-stg-001)、[ACC-STG-006](../testing/acceptance.md#acc-stg-006)

<a id="req-stg-002"></a>

## REQ-STG-002 候选身份、准备就绪、应用核对和生效修订

责任模块为 `stage`。

准备或应用展台时，stage 将候选绑定项目修订、OBS 连接代际、目标、计划内容及有效期。

准备阶段只读取 OBS。应用前重新核对目标并等待布局就绪，应用后回读来源、变换、可见性及输出地址。背景只在布局最低层绘制，上层保持透明，捕获框饰遵循显式层序，透明皮肤和空布局分别呈现其预期画面。应用结果提供输出身份、实际生效修订及稳定槽位，后续输出查询返回固定摘要。同一项目在不同实际目标或场景的输出可以并存，同槽位再次应用替换原输出；每个实际目标场景同时只有一个项目拥有受管布局，跨项目替换在准备时显式授权，跨 profile 先由原 profile 释放。

[展台与 OBS 设计](../design/stage-obs.md) · [ACC-STG-002](../testing/acceptance.md#acc-stg-002)、[ACC-STG-004](../testing/acceptance.md#acc-stg-004)

<a id="req-stg-003"></a>

## REQ-STG-003 应用幂等、失败补偿及用户资源保护

责任模块为 `stage`。

重复提交展台应用或在部分写入后失败时，stage 使用原操作身份核对目标并执行有条件的补偿。

同名来源先核对身份、类型与归属，手动创建的同名同地址来源保留原归属。既有场景项进入受管排序须有明确排序权限，未授权时使用新的场景引用或在准备阶段返回具体冲突。受管展台场景项在目标场景底部按布局层序排列，其他场景项的相对顺序和来源设置保持原值，共享来源的其他引用保持有效。恢复保护既有资源及用户后续修改，部分恢复列出剩余对象和具体冲突，继续恢复沿用原操作。新候选完成核对后切换槽位，再清理旧输出；切换后的旧清理失败保留新 owner。旧输出仍被外部引用时以 retained 保留完整资源及访问，引用归零后重新核对并回收。显式释放沿原操作串行完成，活动输出释放失败继续占用原槽位，恢复完成后撤销令牌及订阅。

[展台与 OBS 设计](../design/stage-obs.md) · [ACC-STG-003](../testing/acceptance.md#acc-stg-003)、[ACC-STG-005](../testing/acceptance.md#acc-stg-005)

<a id="req-mcp-001"></a>

## REQ-MCP-001 单一工具注册、提供方发现、能力组、Schema、错误和实际互通

责任模块为 `entrypoints`。

启动 MCP 接入、发现提供方、启用能力组或调用工具时，entrypoints 使用单一类型化注册来源生成接口资料与路由。

连接建立前可以发现提供方与配置要求，实际能力来自已安装适配器和目标连接。Schema、结构化通知、错误与取消在所选真实客户端中按契约互通。

[MCP 契约设计](../design/mcp-contract.md) · [ACC-MCP-001](../testing/acceptance.md#acc-mcp-001)、[ACC-MCP-003](../testing/acceptance.md#acc-mcp-003)、[ACC-MCP-004](../testing/acceptance.md#acc-mcp-004)

<a id="req-mcp-002"></a>

## REQ-MCP-002 大型集合默认分页、稳定游标与独立详情

责任模块为 `entrypoints`。

查询事件、音色、模型、映射、媒体、预设、操作或其他可增长集合时，接入层使用一致的默认分页和独立详情接口。

业务列表默认 50 条、上限 200 条，游标绑定运行配置、数据代际、筛选、排序和快照。可变集合的列表快照固定成员、摘要和排序，后续状态修改或删除保持旧快照内容，详情返回对象当前值。快照受有效期和容量预算约束，过期返回 CURSOR_EXPIRED，非事件集合从首页建立新快照，事件在同一代际内按水位续读。大文件通过资源引用读取，协议目录与业务分页分别完成。

[MCP 契约设计](../design/mcp-contract.md) · [ACC-MCP-002](../testing/acceptance.md#acc-mcp-002)、[ACC-MCP-003](../testing/acceptance.md#acc-mcp-003)、[ACC-MCP-004](../testing/acceptance.md#acc-mcp-004)

<a id="req-sec-001"></a>

## REQ-SEC-001 凭据、路径、输出令牌和工具访问范围

由各模块负责所属对象的授权与校验，infrastructure 提供凭据和路径校验设施，entrypoints 执行接入权限检查。

保存凭据、解析文件路径、访问展台输出或执行有副作用工具时，相应模块按运行配置、目标对象和操作范围授权。

密钥使用系统凭据库，配置、导出和日志保留必要引用并过滤明文。路径按实际解析目标约束，只读输出令牌限定候选及资源范围，撤销后终止其持续数据访问。本地 Web 校验目标主机、请求来源、会话和跨站写入凭据，WebSocket 同样校验来源与会话。外部消息按文本显示，富文本仅接受明确允许的结构和链接。

[访问与资源设计](../design/security.md) · [ACC-SEC-001](../testing/acceptance.md#acc-sec-001)、[ACC-SEC-002](../testing/acceptance.md#acc-sec-002)

<a id="req-eng-001"></a>

## REQ-ENG-001 可复现依赖、独立制品和UTF-8标准流

责任主体为构建与制品维护者，bootstrap 和 entrypoints 负责安装入口与标准流。

建立开发环境、构建安装包或运行 stdio MCP 时，工程采用 CPython 3.12 系列、明确依赖输入及独立安装制品。

安装后从包内加载静态资源，可选提供方隔离。源码、配置、日志和标准流按 UTF-8 处理，stdout 承载协议，中文路径、管道和 Windows 命令入口保持正确编码。

[工程约定](../development/engineering.md) · [ACC-ENG-001](../testing/acceptance.md#acc-eng-001)、[ACC-ENG-002](../testing/acceptance.md#acc-eng-002)

<a id="req-perf-001"></a>

## REQ-PERF-001 参考负载下的时延、容量与持续稳定性

runtime 协调测量入口，各模块负责所属链路的性能结果。

在规定的参考环境和负载下，按阶段测量本地接口、事件持久与通知、播放启动、字幕、嘴型、语义调度、页面绘制及恢复。首版基准采用三平台合计持续 100 事件/秒、每五分钟一次 500 事件/秒的五秒突发、百万历史及四个 MCP 客户端。

核心接口 P95 不超过 100 ms，200 条分页 P95 不超过 200 ms；字幕与嘴型同步 P95 不超过 100 ms。具体起止点、P99、其他链路阈值、30 分钟基准及两小时稳定性按性能规格执行。主进程与子进程内存稳态 P95 不超过 768 MiB、峰值不超过 1 GiB；突发后十秒恢复持续负载时延目标。各适配器同时记录完整端到端及本地分段结果。

[性能验收规格](../testing/performance.md) · [ACC-PERF-001](../testing/acceptance.md#acc-perf-001)
