# 术语表

本文是中文（zh-Hans）与英文术语参考，面向设计、接口、指南和测试的编写者及接入开发者。代码标识符采用协议或模型的准确拼写。

## 产品与领域

| 中文 | 英文或标识符 | 含义 | 使用上下文 |
| --- | --- | --- | --- |
| 调用方 Agent | calling agent | 负责回复与任务决策，并通过工具调用服务的程序 | 产品、调用指南 |
| 提供方 | provider | 实现某类服务能力的适配渠道 | 发现、语音、转写和平台连接 |
| 连接 | connection | 绑定提供方、配置、凭据引用和观察状态的服务目标 | 连接配置及工具参数 |
| 运行配置 | profile | 隔离应用设置、连接、数据及操作的运行范围 | 启动、持久化、游标与授权 |
| 文本转语音 | text-to-speech，TTS | 从文本生成语音 | speech |
| 语音转文本 | speech-to-text，STT | 从音频获得转写结果 | transcription |
| 发声标签 | vocal tag | 提供方支持时用于控制笑声、语气等效果的文本标签 | TTS 合成正文 |
| 字幕投影 | subtitle projection | 从播放正文生成面向观众的字幕视图 | stage |
| 语义映射 | semantic mapping | 将关键词、排除词和标签关联到模型参数意图的配置 | performance |
| 追踪输入 | tracking input | VTS 接收并按模型配置转换的输入，如 MouthOpen | 模型能力与输入注入 |
| 内部模型身份 | model_id | 运行配置内唯一、绑定 VTS connection_id 与 provider_model_id 的稳定模型身份 | 模型配置、离线保存及跨连接隔离 |
| 原生模型身份 | provider_model_id | VTS 连接中发现的模型标识，同值可出现在不同连接 | 模型发现与内部身份绑定 |
| 模型输出参数 | model output parameter | 实际控制 Live2D 形变的模型参数，如 ParamMouthOpen | 输入映射与最终冲突判定 |
| 嘴型同步 | lip sync | 根据实际播放音频驱动嘴部通道 | 音频包络与 avatar |
| 表情 | expression | 对模型参数施加预设覆盖或叠加的效果 | VTS 表情与组合 |
| 热键 | hotkey | VTS 中触发动作的入口，具体 ID 绑定当前模型代际 | 热键发现与逻辑绑定 |
| 展台 | stage | 组织布局、组件、媒体及播出候选的项目 | 编辑、预检及应用 |
| 来源 | OBS source / input | OBS 中可被场景项引用的内容对象 | OBS 绑定与资源归属 |
| 场景项 | OBS scene item | 某来源在特定场景中的引用及变换、可见性 | 布局应用与恢复 |
| 浏览器平面 | browser plane | Web 内容的合成平面，不透明皮肤使用独立最低背景平面，上层组件与捕获框饰按层序组成透明平面，透明皮肤保持真实透明背景 | 展台层序与 OBS 合成 |
| 醒目留言 | Super Chat，SC | 带有金额、完整留言和展示时间等业务信息的平台事件 | 直播事件 |
| 事件来源快照 | source | 接收时真实房间或频道的 source_id，以及上游提供的 display_name、broadcast_id | 历史来源、路由及上游身份去重 |

## 状态与协调

| 中文 | 英文或标识符 | 含义 | 使用上下文 |
| --- | --- | --- | --- |
| 修订 | revision | 同一配置或项目内容的版本序号 | 并发更新与配置应用 |
| 已保存修订 | saved_revision | 已完成持久事务的期望配置 | 配置回执 |
| 活动修订 | active_revision | 模块当前已应用的配置 | 配置激活与重启恢复 |
| 代际 | generation | 连接重建、模型加载或播放替换后区分新旧执行环境的标记，重新加载同一模型保留内部身份并更新模型代际 | 回调、计划和写入校验 |
| 数据代际 | data_generation | 当前持久数据集的身份，数据恢复切换后更新 | 事件水位、游标及恢复隔离 |
| 组件状态序列 | state_sequence | 同一组件内排序运行及内容状态的递增序列 | 字幕显示、隐藏及状态同步 |
| 操作 | operation | 一次逻辑命令的生命周期及实际效果记录 | 长操作查询与恢复 |
| 幂等键 | idempotency_key | 使同一逻辑操作的重复提交关联到原操作的键 | 有副作用命令 |
| 预检计划 | preview / prepared plan | 绑定修订、目标、代际及有效期的应用计划 | stage_prepare |
| 参数租约 | parameter lease | 对实际目标、模型代际及完整输出参数集合的控制权，每次授予具有独立 lease_id | 整组仲裁、写入与释放 |
| 入队序号 | enqueue_sequence | 同数据代际中受理时持久递增的语音顺序，同级按其先进先出 | 播放队列与幂等 |
| 授予身份 | lease_id | 区分每次参数控制授权，同 owner 重新获授后旧写入及释放失效 | 参数控制与恢复 |
| 消费水位 | consumer watermark | 消费者已处理到的 data_generation 与本地序列，续读携带同代际并以 after_sequence 作为排他下界 | 通知、历史补拉与恢复 |
| 接收序列 | sequence | 当前运行配置及 data_generation 内按持久接收顺序递增的事件位置 | 通知去重、历史分页与续读 |
| 配置范围 | section / scope_id | 配置分区与连接、模型或项目范围共同确定的配置对象 | 保存、导入及重新激活 |
| 输出身份 | output_id | 一次展台应用形成的持续输出对象，与开始应用的预检有效期分别管理 | 展台查询、替换与恢复 |
| 输出槽位 | output_slot_id | profile、项目、实际 OBS 目标和场景共同确定的稳定应用位置，重连保持该身份 | 输出并存与替换 |
| 保留输出 | retained | 被替换且仍有计划外引用的旧输出，保留原资源及只读访问并退出活动槽位 | 引用保护与回收 |
| 播放时钟 | playback_clock | 实际播放位置来源，取值为 pcm、provider_timestamp 或 native_lifecycle，播放事件由 clock.kind 承载 | 播放事实、分句调度及状态查询 |
| 正文对齐来源 | alignment_source | 合成正文码点区间与音频区间关联的来源，取值为 provider_timestamp 或 text_estimate | 字幕分句与语义动作定位 |
| 时钟代际 | clock_epoch | 播放器单调时钟的身份，同代际的 started_monotonic_ms 可用于原生播放调度 | 延迟消费及重启后的时钟隔离 |
| 游标 | cursor | 绑定筛选、排序和快照的分页续读位置 | 集合查询 |
| 结果未知 | outcome_unknown | 外部效果已经可能发生，需按原操作核对的状态 | 超时与故障恢复 |
| 恢复冲突 | RECOVERY_CONFLICT | 当前外部值与本次已确认写入不同，恢复需保护后续修改 | OBS 补偿 |
| 数据代际变化 | DATA_GENERATION_CHANGED | 水位或游标属于旧数据集，需要按当前代际重新建立快照 | 数据恢复后的事件续读 |
| 历史缺口 | HISTORY_GAP | 保留清理已删除续读所需记录，结果提供最早可读序列 | 事件历史及消费恢复 |

## 文档与验收用语

| 中文 | 英文 | 含义与使用方式 |
| --- | --- | --- |
| 必须 | MUST | 已确定适用条件下的必要要求 |
| 不得 | MUST NOT | 已确定适用条件下禁止的行为 |
| 建议 | SHOULD | 有明确理由时可以选择其他方案的建议 |
| 可 | MAY | 在约定条件下允许选择的能力或做法 |
| 未执行 | not-run | 对应检查尚未执行 |
| 不适用 | not-applicable | 对应机制的触发条件不成立 |
| 未知 | unknown | 对应结果尚不能由当前观察确定 |
| 失败 | failed | 已执行检查或操作的结果不满足对应判据 |
| 需求规格 | requirements specification | 规定主体、条件和可观察结果 |
| 设计 | design | 说明满足需求的机制、状态与责任接口 |
| 参考 | reference | 提供术语、字段及协议事实的查阅入口 |
| 指南 | how-to guide | 按实际任务给出前置、步骤、预期与恢复 |
| 架构决策记录 | architecture decision record，ADR | 记录技术选择的背景、选项、理由、代价和重新选择条件 |

字段结构见共享契约，操作状态转换见运行时设计。

[工具与数据契约](../../contracts/README.md) · [运行时设计](../design/runtime.md)
