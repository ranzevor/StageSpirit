# 内部接口与协调责任

本文面向跨模块接口的提供方和消费者，规定输入输出、协调边界、时间语义及失败恢复责任。

跨模块接口只传递版本化数据、稳定身份和明确的执行条件。连接客户端、数据库会话和模块私有对象由其所属模块持有。

## 接口边界

| 接口 | 提供方与消费者 | 输入与结果 | 并发及失败责任 |
| --- | --- | --- | --- |
| SpeechService | speech → MCP、触发动作分发器 | 语音请求 → 操作回执与音频资源 | speech 负责队列及播放；runtime 负责同一幂等操作只受理一次 |
| PlaybackEvent | speech → stage、performance、avatar | 数据代际、语音连接、播放身份、正文、发生时刻及实际时钟 | 消费者拒绝旧代际；自身故障不阻塞播放器 |
| AudioEnvelope | speech → avatar 嘴型驱动 | PCM 包络、采样位置、播放代际 | 过时音量可合并；结束和释放信号必须送达 |
| PlaybackAlignment | speech → performance、stage | 按数据代际、语音连接、播放身份及正文修订读取提供方对齐描述和资源 | speech 规范化码点与音频区间；消费者按对齐修订读取有界 cue 区间 |
| PlaybackAlignmentChanged | speech → performance、stage | 播放及正文身份、已发布对齐修订和可用状态 | 对齐记录与通知同事务发布，消费者只重建尚未触发的后续片段 |
| AvatarControl | avatar → MCP、嘴型驱动、performance | 带稳定意图身份、来源及代际的参数或动作意图；语义按目标调度步提交固定候选批次 → 整组租约与实际执行结果 | avatar 解析最终输出，按整组授予或拒绝；写入和释放核对当前 lease_id |
| ConfigurationParticipant | 各业务模块 → settings | 配置候选 → 校验结果、激活计划和活动修订 | 模块负责语义校验与激活；settings 负责持久事务 |
| EventActionDispatcher | 各动作模块 → live_events | 已持久化动作计划 → 操作回执 | live_events 固定事件、规则修订与动作身份；目标模块执行 |
| BroadcastControl | broadcast → stage、MCP | 资源租约、目标前置条件及写入 → 实际观察结果 | broadcast 串行化同目标写入；stage 决定补偿步骤 |
| StageRevisionChanged | stage → Web 编辑端、预览消费者 | 数据代际、项目、已提交修订、变更类别和状态序列 | stage 与编辑事务一并保存分发记录；快照和续流共用水位，迟到消息不能覆盖新视图 |
| SemanticStatus | performance → MCP、管理端 | 模型及播放身份、活动映射修订、播放时钟、正文对齐来源及有限计数 | 通过 semantic_status_get 查询固定摘要、计数和具体原因，完整计划由内部调度器按资源预算管理 |
| CollectionSnapshot | 各模块 → 查询接入层 | 数据代际、集合读取版本、筛选、排序与有效期 | 模块事务保存版本投影，接入层验证游标与租约，过期后重新建立读取上下文 |

## 事件身份与时间

播放事件的 [Schema](../../contracts/schemas/playback-event.schema.json)规定播放代际和时钟来源。字幕通过[字幕视图](../../contracts/schemas/subtitle-state.schema.json)单独输出；合成正文保留在播放事实中，performance 从该正文生成独立匹配视图。

播放订阅绑定运行配置和语音连接，再由消费者配置选择 VTS 目标或字幕组件。一个连接的播放事实只进入匹配的订阅，消费时继续校验模型及播放代际。

墙上时间 occurred_at 用于记录发生时刻，单调时间和已播放采样位置用于调度。播放位置只在同一播放代际内比较。native_lifecycle 的实际启动事件携带 started_monotonic_ms 与 clock_epoch，消费者沿用播放器发布的起点；不同时钟代际的单调数值不相减。系统语音仅有生命周期时，不发布 PCM 进度。

playback_clock 表达位置推进的时钟，alignment_source 表达合成正文区间与音频区间的对应来源。有 PCM 但没有正文时间戳时，使用 PCM 推进实际播放位置，以 text_estimate 产生分句对齐。字幕和语义调度保留同一合成正文的码点区间映射。

PlaybackAlignment 按播放身份与正文修订返回提供方对齐的可用状态、对齐修订、时间轴单位及资源引用。cue 描述合成正文码点区间到音频区间的对应关系，按范围有界读取；流式结果通过 PlaybackAlignmentChanged 发布新的可用修订。尚未取得提供方对齐时，performance 和 stage 各自在其调度视图中选择 text_estimate，并沿原播放时钟推进。

模型、连接和播放各自维护代际。模型代际改变后，旧模型动作、映射解析和待发送参数批次失效；连接代际改变后，旧目标预检需要重新读取。

## 配置事务

1. 业务模块校验候选并准备不可变活动快照。
2. settings 在事务内检查期望修订，写入期望配置和激活记录。
3. 事务提交后，业务模块切换快照或重建连接，并更新活动修订。
4. 激活失败记录具体分区与错误；再次应用使用同一已保存修订。重启恢复未完成的配置激活记录。

外部网络调用不占用数据库写事务。settings_apply 再次应用当前已保存修订；传入更早修订返回 REVISION_CONFLICT。未加载模型的配置完成结构保存后保留未激活原因，在目标模型加载后按同一保存修订继续能力校验与激活。配置恢复只应用设置，播放、推流和录制等一次性动作由操作账单独管理。

数据恢复在独立维护控制状态中准备新 data_generation，并在切换时发布。旧代际通知和回调只参与其原操作的核对；新动作和条件写入必须使用当前代际。

## 控制与补偿

参数租约由 avatar 发放，包含唯一 lease_id、所有者、实际目标、模型代际、完整最终输出集合、到期时间和释放方式。调用方不能直接修改租约表。写入、续期、撤销和释放必须同时匹配所有者、代际和当前授予身份，同 owner 再次获授也使用新 lease_id。整组输出在同一目标协调边界内授予或拒绝，高优先抢占撤销旧意图的完整租约；不能安全停止的原生控制继续占用。互斥表情组切换、覆盖授权、同级竞争及实际部分失败分别按[参数控制权](../design/avatar-performance.md#参数控制权)处理。

OBS 资源租约由 broadcast 发放；stage 与直接 OBS 工具共用它。同 target_id 下的全局来源、场景项与场景排序分别确定锁集合，共享来源的写入覆盖其引用范围；多资源按固定顺序取得租约。补偿前比较当前对象身份和上次已确认写入的属性；出现外部变更时保留当前值并报告冲突。

这些保证分别落实在[运行时](../design/runtime.md)、[形象与表演](../design/avatar-performance.md)、[展台与 OBS](../design/stage-obs.md)的状态转换中。
