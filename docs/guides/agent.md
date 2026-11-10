# Agent 调用指南

本文面向编写 StageSpirit 调用流程的 Agent 作者，按具体任务说明前置、调用步骤、可观察结果与恢复方式。流程依据本项目的工具契约设计编写，参数结构和枚举在接口参考中查询。

[MCP 接口参考](../reference/mcp.md) · [工具与数据契约](../../contracts/README.md)

## 服务发现与连接

接入前需要服务运行配置及相应目标的连接信息。core 工具始终可用。先调用 runtime_status 取得当前 profile_id 与 data_generation，后续变更请求携带该代际。通过 settings_get 读取 runtime 分区，以 settings_save 更新 enabled_capability_groups 后，再按以下顺序配置连接。

1. 调用 provider_list，按服务类型选择提供方，并按游标读取所需目录。
2. 调用 provider_get，读取该提供方要求的配置字段和声明能力。
3. 更新既有连接时，先调用 connection_get 取得当前修订。使用 connection_save 保存配置，创建时 expected_revision 为 0。
4. 检查保存回执的 saved_revision、active_revision 和具体错误，确认配置的保存及激活状态。
5. 连接尚未建立时调用 connection_connect，保存返回的 operation_id，再通过 operation_get 读取连接结果。
6. 连接建立后调用 runtime_capabilities，按目标的实际能力选择后续工具和参数。

配置被拒绝时按具体字段修正输入。修订冲突时读取当前值并核对本次变更，连接失败时查看该连接的实际错误。目录修订或连接代际变化后刷新相关缓存。

## 说话与字幕

开始前需要可用的语音连接，或已经指定的默认语音连接。确认提供方实际支持的音色、风格、速率、音高和发声标签。

1. 使用 voice_list 查询音色，检查 metadata 中的来源与发现状态，按语言筛选并分页读取。需要模型或后端选项时调用 voice_get。刷新时创建新查询，续页保留原 cursor。
2. 使用自然短句、停顿和适量语气词组织正文，保留数字、单位、否定及必要条件。逐字朗读选择 verbatim，普通口语选择 spoken。
3. 提供方支持时，使用 style 风格提示或正文发声标签表达语气。根据想呈现的情绪选择提示，避免无关表演描述挤占播报正文。
4. 调用 speech_speak 合成并播放，保存操作身份。只需要音频文件时调用 speech_synthesize。
5. 通过 operation_get 查看播放或合成结果。需要停止时使用 speech_stop，明确指定目标操作。

priority 取 0 至 9、默认 5，数值大者优先，同级按受理顺序播放；任务取得播放权后本次选择固定。需要立即替换当前播报时显式使用 interrupt_current，受理后请求停止当前声音并保留下一播放权，确认停止和资源释放后开始新声音。PLAYBACK_SWITCH_BUSY 时沿原切换操作查询，QUEUE_FULL 时等待或停止明确不再需要的待播操作。普通优先级调整保持在播声音继续。

~~~json
{
  "data_generation": "profile-generation-01",
  "text": "真的成功了！[laughter] 咱们接着聊。",
  "text_mode": "spoken",
  "idempotency_key": "speech-example-001"
}
~~~

此例的 data_generation 使用合成示例值，实际调用填写 runtime_status 返回的当前代际，并使用默认语音连接。ASCII 方括号内容原样传给 TTS，字幕隐藏全部 ASCII 方括号块及其中内容。spoken 模式过滤已识别的中文括号表演提示，正常说明保留。普通语音请求按语音参数填写。

目录来源为 configured 时，读取到的是当前配置音色，complete 为 false。metadata.state 为 unsupported 时，在 provider_get 查询该适配器支持的目录端点或手工目录配置；为 failed 时按目录错误处理后刷新。ready 且 items 为空表示本次目录查询没有匹配项。参数不受支持时按 runtime_capabilities 调整，超时按原操作身份查询。

[语音请求示例](../../examples/contracts/speech-request.json) · [语音与字幕设计](../design/speech.md)

## 配置语义动作

开始前需要目标模型身份、当前映射修订及 VTS 连接。model_id 使用模型目录返回的内部身份，详情中的 connection_id 与 provider_model_id 标明对应 VTS 连接及原生模型。语义动作的配置由独立工具维护，普通语音播放自动消费活动配置。

1. 使用 avatar_parameters_list 分别查询 tracking_input、model_output 和 mapping，确认输入、输出、范围和实际映射。
2. 使用 settings_get 读取 performance 分区，以 model_id 作为 scope_id，取得 enabled、维护说明及当前修订。使用 semantic_mappings_list 查询已保存条目，使用 semantic_mapping_get 读取需要修改的完整条目。
3. 为当前模型配置关键词、排除词、参数、过渡时间和规则优先级，使用 semantic_mappings_save 保存，并指定 expected_revision、mode 和 enabled。
4. 核对回执的保存与活动修订，再按普通语音流程调用 speech_speak。
5. 在播放中更新规则时，通过同一配置工具保存新修订，观察当前位置之后的片段采用新配置。
6. 调用 semantic_status_get 读取该模型的有限运行摘要，核对活动映射修订、playback_clock、alignment_source、调度位置和暂停原因。

排除词先于命中词处理，语义 priority 默认为 50，数值大者优先，同一调度批次内的同级候选按 mapping_id、model_id 和服务生成的 intent_id 排序。每条映射是一个完整参数意图，任一输出被保护时整条跳过，可独立执行的其他映射继续。配置前核对最终输出，避免同一条映射的不同输入指向同一输出。

参数控制默认按手动参数、明确动作与表情、允许的嘴型、语义细节协调，模型明确允许的嘴部覆盖继续生效。同级明确参数占用时返回 PARAMETER_BUSY，查询占用详情并等其释放；同组表情切换沿原组入口串行执行。动作结束后只恢复当前仍有效的自动控制，过期关键词不会补执行。

修订冲突时读取最新配置再合并。模型重载后重新查询当前输入与映射，配置生效失败时处理回执中的具体原因。关闭语义控制通过 enabled 配置完成，嘴型与明确动作继续使用各自控制权。

[语义映射示例](../../examples/contracts/semantic-mapping.json) · [形象与语义表演设计](../design/avatar-performance.md)

## 处理直播消息

开始前需要已建立的平台连接，以及要处理的事件类型和时间范围。

1. 从通知读取结构化事件，区分聊天、SC、礼物和会员，使用 event_id 去重，保存已处理的 data_generation 与 sequence，并按 source 快照识别事件发生时的房间或频道。
2. 回应时使用完整留言，保留 UID、等级、礼物数量、总价值和单位等业务区别。免费平台积分与 Bits 按原单位表达。
3. 读取历史时使用 event_list，并保持连接、事件类型、用户和时间筛选一致。单条详情使用 event_get。
4. 按 next_cursor 读取后续页，以 has_more 判断分页结束。后续补拉或游标过期时，以同一 data_generation 和最后已处理序列作为 after_sequence 建立新查询。

触发动作绑定事件身份和规则修订。发生重复投递时复用原动作，消费者从已保存水位恢复。HISTORY_GAP 表示请求区间存在已清理历史，读取最早可用序列后明确选择新的消费位置。DATA_GENERATION_CHANGED 表示数据恢复已切换代际，重新取得当前上下文与历史快照，原水位不用于新代际续读。

[直播事件设计](../design/events.md) · [事件契约与示例](../../contracts/README.md#共享模型与关键请求)

## 应用展台

开始前需要已保存的展台项目修订，以及明确的 OBS 连接、场景和来源绑定。

1. 调用 stage_project_get 取得待应用修订，并核对来源绑定。
2. 调用 stage_prepare，读取目标、修订、target_id、output_slot_id、变更摘要和 preview_id，检查背景平面、捕获框饰及每个既有来源的绑定和可写范围。另一项目已占用同一实际目标场景时，在当前 profile 明确选择 replace_output_id 再准备，核对 occupied_output 中的 owner、输出及状态序列。跨 profile 的占用先在原 profile 显式释放。
3. 需要检查具体变更时，使用 stage_preview_changes_list 按同一预检分页读取。准备只读取 OBS，不创建来源或长期占锁。
4. 使用该预检提交 stage_apply，携带匹配的项目修订和本次逻辑操作幂等键，替换授权沿用计划。
5. 保存 operation_id，通过 operation_get 查看执行状态、外部效果及恢复状态。完成后用 result_resource_id 调用 resource_get 取得资源回执，再按 URI 使用 resources/read 或受控下载读取 StageApplyResult。从中取得实际生效修订、output_id、target_id、output_slot_id 及替换时的 replaces_output_id，然后调用 stage_output_get 读取输出状态。
6. 需要撤销输出时，先读取其 state_sequence，再调用 stage_output_release，携带 data_generation、output_id、expected_state_sequence 和本次释放幂等键。沿 operation_get 等待清理完成，并确认输出为 released 且不再返回 URL。

同一项目应用不同实际目标或不同场景时，已有输出继续提供服务。同一目标场景再次应用替换该槽位原输出。重连不改变槽位。替换后的旧输出仍被外部引用时为 retained，继续提供原布局和只读 URL。引用数量在 retained_reference_count 中读取，引用详情按 details_resource_id 的资源入口分页读取。引用归零后服务重新核对并安排释放。显式释放保留外部引用的输入，完成后撤销该输出访问。

PLAN_EXPIRED 或 TARGET_CHANGED 时重新准备受影响目标。OUTPUT_CONFLICT 时读取实际归属与状态，已有未完成应用、释放或恢复时先查询原 operation_id，必要时停止原候选并沿 stage_restore 处理。不以新释放绕过原操作。RESOURCE_LIMIT 时先释放明确不再使用的输出或资源，再准备新候选。超时先查询原操作，恢复使用 stage_restore 指向原应用或释放操作。RECOVERY_CONFLICT 时查看具体冲突项，保护当前外部修改。失败释放在原恢复完成前继续保留原槽位占用。

Web 编辑端会收到同一项目修订的变更。布局修改先更新草稿预览，应用完成后切换播出布局；运行数据按组件状态序列持续更新。预检过期时重新准备，已经应用的输出继续按其生命周期提供服务。

[展台应用示例](../../examples/contracts/stage-apply.json) · [释放示例](../../examples/contracts/stage-output-release.json) · [展台与 OBS 设计](../design/stage-obs.md)

## 配置导入与数据恢复

1. 使用 settings_export 导出当前运行配置。回执提供资源身份、URI、媒体类型和大小。
2. 使用 settings_import 的 preview 模式检查导入资源、目标修订、strategy 与删除范围，按同一预览提交 commit。保存成功后分别检查各分区激活状态。
3. 需要数据备份时调用 settings_backup，等待原操作完成后读取备份资源。
4. 使用 settings_restore 预览所选备份的版本、媒体和目标差异，再以同一预览及目标修订提交恢复。维护阶段由服务协调停止受影响写入，完成后查询恢复结果。
5. 数据恢复完成后重新调用 runtime_status 取得新的 data_generation，再读取配置、模型和项目修订。恢复前的游标、预检和输出授权重新建立，OBS 实际输出通过新的准备及应用操作核对。

凭据按目标设备重新绑定。MIGRATION_REQUIRED 使用错误指定的版本与恢复资源执行维护，REVISION_CONFLICT 重新读取目标修订并生成预览。

[配置与恢复设计](../design/storage.md) · [导出示例](../../examples/contracts/settings-export.json)

## 查询和恢复

列表使用 limit、cursor 和相同筛选续读，已经取得当前任务需要的对象即可结束查询。可变列表的摘要属于固定快照，详情返回当前对象；迟到列表摘要不覆盖已经取得的新修订。普通列表游标过期后从首页新建快照，事件查询按同代际水位续读。音频、媒体和完整配置通过资源引用取得。结果只包含 resource_id 时，调用 resource_get 取得访问回执。

长操作保存 operation_id 和幂等键。相同逻辑重试沿用原键，新的任务使用新键。请求超时后先查询原操作的执行状态与实际效果，再按工具恢复契约处理。请求取消使用 operation_cancel，并继续观察最终状态。

配置保存、连接建立、业务执行及外部效果分别读取对应结果。配置已经保存但尚未应用时，读取具体分区和修订，通过 settings_apply 指定相同 section、scope_id 和保存修订进行应用。

[MCP 回执与错误](../reference/mcp.md#命令与回执) · [操作生命周期](../design/runtime.md)
