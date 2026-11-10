# 工具与数据契约

本文供接口设计和接入开发查阅，集中说明工具边界、共享 Schema、关键请求响应、示例及应用层不变量。

[工具目录](tool-catalog.json)登记工具边界、能力组、输入语义、结果类型和分页要求。实现阶段由类型化注册表生成完整工具接口，引用这些共享 Schema，按本目录核对业务含义。目录内的 input 是字段语义说明，关键请求的具体类型由其 input_schema 规定，其余完整输入输出在实现所属阶段形成。

## 共享模型与关键请求

| 对象 | Schema | 示例 |
| --- | --- | --- |
| 分页、回执、错误和价值单位 | [共享定义](schemas/common.schema.json) | 各查询和回执消费 |
| 直播事件 | [事件](schemas/live-event.schema.json) | [SC](../examples/contracts/event-superchat.json)、[免费礼物](../examples/contracts/event-free-gift.json)、[Bits](../examples/contracts/event-bits.json)、[匿名会员事件](../examples/contracts/event-member.json) |
| 音色目录 | [分页与状态](schemas/voice-page.schema.json) | [当前配置值](../examples/contracts/voice-page-configured.json)、[服务返回空目录](../examples/contracts/voice-page-empty.json) |
| 语音播放 | [播放请求](schemas/speech-request.schema.json) | [发声标签](../examples/contracts/speech-request.json) |
| 仅合成 | [合成请求](schemas/synthesis-request.schema.json) | [合成](../examples/contracts/synthesis-request.json) |
| 播放事实 | [播放事件](schemas/playback-event.schema.json) | [原始合成正文](../examples/contracts/playback-event.json) |
| 字幕视图 | [字幕](schemas/subtitle-state.schema.json) | [清理后的正文](../examples/contracts/subtitle-state.json) |
| 语义配置 | [映射](schemas/semantic-mapping.schema.json) | [独立映射](../examples/contracts/semantic-mapping.json) |
| 语义运行状态 | [有限摘要](schemas/semantic-status.schema.json) | 播放时钟、正文对齐、活动修订与暂停原因 |
| 配置生效 | [配置回执](schemas/configuration-receipt.schema.json) | [已保存但应用失败](../examples/contracts/configuration-receipt.json) |
| 展台准备 | [预检结果](schemas/stage-preview.schema.json) | [预检](../examples/contracts/stage-preview.json) |
| 展台应用 | [应用请求](schemas/stage-apply.schema.json) | [应用](../examples/contracts/stage-apply.json) |
| 展台输出、完成结果与释放 | [输出、StageApplyResult 和 StageOutputRelease](schemas/stage-output.schema.json) | 操作结果资源取得 output_id，再查询摘要；[显式释放](../examples/contracts/stage-output-release.json) |
| 操作与恢复 | [操作详情](schemas/operation-detail.schema.json) | [结果核对中](../examples/contracts/operation-detail.json) |
| 配置导出 | [导出](schemas/settings-export.schema.json) | [导出配置](../examples/contracts/settings-export.json) |

示例使用合成身份与数据。data_generation 为对应运行配置的数据集身份，示例值在实际调用中由 runtime_status 返回。模型参数的可写性和范围由应用层核对当前模型，JSON Schema 负责结构与值域。Schema 的 default 是接口默认值说明，接入层按工具规则填充默认值，默认连接在首次受理时解析并固定；结构校验器本身不修改请求。

## 应用层不变量

- 所有业务变更请求携带 data_generation，修订、水位、游标和运行状态序列在该数据代际内比较。恢复数据生成新代际；旧请求仅可查询已受理原操作，不能新受理动作。
- 语音省略 connection_id 时使用该运行配置的默认语音连接。播放请求与仅合成请求分开，语义映射不进入普通语音输入。priority 为 0 至 9、默认 5，按数值降序及持久 enqueue_sequence 升序派发；starting 后选择固定。interrupt_current 受理后停止当前并保留一次下一播放权，同槽位已有切换时返回 PLAYBACK_SWITCH_BUSY。待播默认 64、合成并发默认 2，满额返回 QUEUE_FULL。
- 字幕源于同一播放身份与正文修订，方括号清理不修改合成正文。state_sequence 对同一组件的显示与隐藏排序，初始 hidden 可无播放关联字段。PCM 时钟的位置来自实际已播放采样，native_lifecycle 不产生 progress；原生播放沿真实起点与 clock_epoch 调度。playback_clock 与 alignment_source 分别描述播放位置和正文对齐。
- 事件 sequence 在同数据代际内唯一递增，source 保留接收时的实际来源快照；上游缺失的发生时间和观众字段保持省略。自定义平台价值包含原单位名称，单价与总价的单位及数量关系在归一化时校验。
- 配置状态为 applied 时，saved_revision 与 active_revision 相等；应用失败保留前一活动修订和具体错误。
- 配置导出按 section 与 scope_id 保留独立范围，profile_revision 为导出来源运行配置的整体修订，导入时另外校验目标 expected_revision。导入拒绝重复范围，并校验各分区值和凭据引用。
- 语义 merge 按 mapping_id 更新，replace 替换该模型映射集合。批次 mapping_id 唯一，条目内 input_name 唯一，排除词先于命中词；省略 priority 按 50 处理，同一调度批次按 priority 降序、mapping_id、model_id、生成的 intent_id 升序仲裁，已跳过命中不跨批次重提。每次命中的完整输出集合整组授予或跳过，同意图不同输入解析到重叠输出时应用层返回 PARAMETER_CONFLICT。明确参数同级先持有者保持控制，后到返回 PARAMETER_BUSY，互斥表情组仍串行切换。每次授予的 lease_id 用于隔离同 owner 的新旧写入及释放。
- stage_prepare 的计划绑定 data_generation、profile_id、修订、连接代际、target_id、场景身份、output_slot_id 及占用输出摘要。槽位由 profile、项目、实际目标和场景确定，重连保持槽位。stage_apply 在跨进程目标场景租约内再次核对；跨项目替换授权 replace_output_id 在 prepare 固定，占用漂移返回 OUTPUT_CONFLICT。plan_digest 对应完整计划内容，对象权限另行校验。
- 音色目录即使 items 为空仍提供 metadata。configured 来源的 complete 为 false；目录发现失败保留 error。voice_list 的刷新与游标续读互斥。
- 预检有效期只限制开始应用，已应用 output_id 的访问由输出生命周期管理。不同目标或场景输出并存，同槽位更新替换原输出。新输出核对后先切换槽位，再清理旧输出；计划外引用使旧输出进入 retained，保持资源与只读访问，引用明细通过详情资源分页。stage_output_release 核对 expected_state_sequence 并沿原操作串行释放，失败保留原槽位直至恢复完成；released 撤销令牌及订阅且没有 output_url。
- 操作 outcome_unknown 使用原操作进行核对；completed 的外部效果必须已确认或明确没有外部效果。展台应用成功结果资源符合 StageApplyResult，输出摘要符合 StageOutput。
- 可变集合分页固定读取版本的成员、摘要和排序，续页不受后续变更影响。CURSOR_EXPIRED、DATA_GENERATION_CHANGED 与 HISTORY_GAP 分别表达读取租约过期、数据代际变化和历史区间已清理。
- model_id 是运行配置内绑定 VTS 连接与 provider_model_id 的内部身份；semantic_status_get 查询有限运行摘要，映射集合使用独立分页接口。

跨字段数值相等、对象归属、唯一身份和状态时序由应用层检查。对应预期在[验收场景](../docs/testing/acceptance.md)维护。

## 展台编辑

stage_edit 使用可区分联合类型，每条命令包含 type 和该变体字段。

| 变体 | 输入 |
| --- | --- |
| set_layout、set_skin | 类型化布局或皮肤 |
| apply_preset | 预设和明确覆盖项 |
| upsert_widget、remove_widget | 组件身份和变更 |
| set_whiteboard_text、clear_whiteboard、append_strokes | 白板、文本或笔迹批次 |
| set_notices、notice_action、chat_action | 对象、业务条目及动作 |
| hide_subtitle | 字幕组件和当前播放身份 |
| undo、redo | 当前修订和历史位置 |

编辑批次在本地事务内全部提交或拒绝，并在同一事务保存修订通知。MCP 与 Web 使用同一提交及读取接口。组件详情中的笔迹、公告和聊天提供分页入口。布局与皮肤变更等待应用，内容变更提交后向已有输出发布组件状态，具体同步方式见[展台设计](../docs/design/stage-obs.md#web-与-mcp-状态同步)。大集合和计划变更分页读取，完整导出使用资源引用。

## 接口测试

测试覆盖结构、必填字段、边界值和错误语义。请求与响应示例见上表，反例按 Schema 类别放在 tests/fixtures/contracts/。业务场景见[验收设计](../docs/testing/acceptance.md)。
