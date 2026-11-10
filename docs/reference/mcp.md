# MCP 接口参考

本文供 Agent 接入开发者查阅，描述首版 stdio MCP 的工具组织、发现、分页、回执、错误及通知契约。

首版使用 stdio。互通矩阵随所属能力实现覆盖目录、调用、资源、通知、取消与错误。

## 当前运行入口

D1 首批注册 `runtime_status`，输入为 `{}`。互通基线为 MCP `2025-11-25`，服务端和测试客户端使用 uv.lock 中的 MCP Python SDK 2.3.0。启动及客户端配置见项目首页。

| 返回字段 | 含义 |
| --- | --- |
| profile_id | 当前运行配置 ID |
| data_generation | 该配置的持久数据代际，普通重启时保持 |
| instance_id | 本次启动的实例身份 |
| version | 当前安装的 StageSpirit 版本 |
| state | 当前实例状态，运行时为 running |
| process_id | 服务进程 ID |
| started_at | UTC 启动时间 |
| uptime_ms | 基于单调时钟计算的运行毫秒数 |
| capability_groups | 已启用的能力组，当前为 core |
| modules | 已装配模块的固定摘要，当前为 runtime / ready |

成功结果的 `structuredContent` 与文本内容来自同一个状态对象。未知工具返回 `-32602`，未知协议方法返回 `-32601`，格式不合法的方法参数返回 `-32602`。错误请求后连接继续处理后续调用。完整字段约束由运行状态 Schema 定义。

[安装与启动](../../README.md#安装与启动) · [运行状态 Schema](../../contracts/schemas/runtime-summary.schema.json)

## 工具组织与发现

工具按 core、live_events、speech、transcription、avatar、performance、broadcast 和 stage 分组。core 提供连接配置、提供方发现、能力查询和操作管理；业务组由运行配置启用，并检查实际已安装适配器。

provider_list 在建立连接前分页列出提供方；provider_get 返回单个提供方的配置字段和能力。runtime_capabilities 查询已建立连接的实际能力。短暂断线保留该组工具并返回连接错误，避免工具目录随网络抖动消失。

目录变更使用所选协议实际支持的通知；客户端按目录修订或连接代际刷新相应缓存。tools/list、resources/list 和 prompts/list 按各自游标获取完整目录，业务工具内部的分页单独处理。

实现时，每个工具从类型化注册表生成输入、输出、说明、分组和副作用元数据。[工具目录](../../contracts/tool-catalog.json)固定设计边界。接入层执行实际权限校验，注解仅描述行为。

## 查询与返回

列表返回完成选择所需的字段，详情按明确身份查询，完整媒体和配置导出返回资源引用。事件正文、UID、等级、金额单位和礼物数量属于业务必要字段，保持完整。

集合使用 limit、cursor 和业务筛选，默认 50 条、最大 200 条，返回 items、next_cursor、has_more。has_more 为 true 时 next_cursor 为非空字符串，为 false 时 next_cursor 为 null。总数仅在低成本可得时以 total_count 返回。

业务结果携带所属 data_generation，runtime_status 提供当前运行配置及数据代际。模型详情中的 model_id 是绑定 VTS 连接与 provider_model_id 的内部身份；连接详情中的 target_id 表示共用外部服务写入协调的目标域。

列表可按所属契约提供 metadata。音色目录的 metadata 包含 state、source、complete 和可用的 fetched_at，发现失败时附带 error；空 items 仍返回目录状态。模型相关目录在元数据中返回 model_generation。详情保留单个对象的必要业务字段，内含的可增长集合另给分页入口或资源引用。

游标绑定运行配置、data_generation、集合、筛选、排序、读取版本和固定有效期，并以服务端签名或受控句柄校验。篡改或跨筛选游标分别返回 CURSOR_INVALID 或 CURSOR_SCOPE_MISMATCH，续页游标必须向前推进。

事件按同一数据代际内的 sequence 升序分页。event_list 的 after_sequence 为排他下界，使用该参数时同时提供 data_generation；首个请求固定快照上界，续页保持原筛选与下界。本次排他续读范围与已清理历史区间相交时返回 HISTORY_GAP 及 earliest_available_sequence；after_sequence 等于最早可读序列减一时可正常续读。数据恢复后的旧水位返回 DATA_GENERATION_CHANGED 和当前代际，调用方重新建立读取上下文。

操作状态、规则、连接等可变列表按所属模块的版本投影固定首请求的成员、摘要与排序，后续修改和删除不改变这份快照。详情返回当前对象及修订，可能比列表摘要更新。首个请求建立有期限的快照租约，跨页释放数据库事务，过期返回 CURSOR_EXPIRED。事件查询在同代际按已处理水位新建查询，其他集合从首页建立新快照并按稳定身份合并结果。实现和回收见[存储设计](../design/storage.md#固定快照与版本回收)。

上游只能全量返回目录时，适配器缓存快照后分页，后续页使用同一目录快照。

资源回执包含 resource_id、uri、media_type 和 size_bytes。操作只给出资源身份时，先通过 resource_get 取得回执，再按 URI 使用 resources/read 或该资源声明的受控下载方式。资源读取继续检查当前运行配置及对象权限。

## 命令与回执

所有业务变更请求携带 data_generation，本地条件写入同时使用 expected_revision。重复保存冲突后通过当前修订核对结果。外部副作用和长操作使用 idempotency_key，查询原 operation_id 取得结果。旧代际的幂等重复仅查询已受理原操作，返回其受理时的 data_generation；当前运行上下文通过 runtime_status 读取。operation_cancel 以目标操作身份天然幂等。传输取消和客户端断开终止当前请求的等待，已受理持久操作使用 operation_cancel 明确取消。

配置通过 section 与可选 scope_id 定位。保存提交后触发激活；settings_apply 沿用相同范围，再次应用当前保存修订，更早修订返回 REVISION_CONFLICT。配置回执分别返回已保存和活动修订，applied 对应两修订相等；active_revision 为 null 表示当前进程尚未激活。操作回执表示受理，操作详情返回完成状态、效果和恢复信息。stage_prepare 返回有限摘要和 plan_resource_id，详细变更通过 stage_preview_changes_list 分页读取。

配置导入的 preview 固定资源、目标修订、strategy 和删除范围，commit 仅提交这一预览。重复提交同一预览读取原提交结果。settings_backup 创建一致数据备份，settings_restore 先预览再在维护窗口恢复，具体规则见[存储设计](../design/storage.md#导入迁移与保留)。

成功调用返回一个类型化业务正文。提供 structuredContent 与兼容文本内容时，二者由同一对象生成，消费端选择一个正文处理。业务校验或执行失败通过 CallToolResult 的 isError 及结构化 Error 表达，已受理操作同时保留 operation_id；无法解析请求、未知工具或非法协议方法由接入层返回协议错误。协议错误码、通知包络与客户端适配在 D1 锁定协议和 SDK 版本时一并验证。

stage_apply 返回操作回执，完成后由 operation_get 的 result_resource_id 取得 StageApplyResult，再读取 output_id 并调用 stage_output_get。结果包含稳定 target_id、output_slot_id 及发生替换时的 replaces_output_id。stage_output_release 按当前 state_sequence 受理，完成后输出为 released；stage_restore 沿原应用或释放操作恢复。semantic_status_get 返回活动映射、播放时钟、正文对齐来源及暂停原因等有限摘要，配置条目仍通过独立配置工具管理。

## 错误契约

| 错误码 | 具体动作 |
| --- | --- |
| INVALID_ARGUMENT | 按字段原因修正输入 |
| CURSOR_EXPIRED | 事件按同代际已处理水位新建查询，其他集合从首页建立新快照 |
| DATA_GENERATION_CHANGED | 读取当前代际，重新取得对象、水位和修订 |
| HISTORY_GAP | 读取最早可用序列，按显式选择重建消费位置并保留缺失区间 |
| RESOURCE_LIMIT | 按返回的资源范围缩小请求或等待资源预算释放 |
| CURSOR_INVALID、CURSOR_SCOPE_MISMATCH | 使用原查询的有效游标及相同筛选 |
| UNSUPPORTED_CAPABILITY | 从该提供方实际能力中选择参数 |
| REVISION_CONFLICT | 读取当前修订并核对已提交内容 |
| CONNECTION_UNAVAILABLE | 查询该目标的连接状态并处理连接错误 |
| QUEUE_FULL | 等待现有队列释放或取消明确的排队任务 |
| PLAYBACK_SWITCH_BUSY | 等待原打断切换结束，重复请求沿原幂等键查询 |
| PARAMETER_BUSY | 按详情确认占用，释放后重试相同逻辑请求；自动意图按整组跳过 |
| PARAMETER_CONFLICT | 修正同一意图中解析到重叠输出的输入集合 |
| OUTPUT_CONFLICT | 读取当前输出归属和序列，已有应用、释放或恢复时先处理原操作，再重新准备或释放 |
| IDEMPOTENCY_CONFLICT | 为不同逻辑操作使用不同键 |
| OUTCOME_UNKNOWN | 查询并核对原操作，保留同一逻辑身份 |
| PLAN_EXPIRED、TARGET_CHANGED | 重新准备受影响的目标计划 |
| RECOVERY_CONFLICT | 查看具体冲突属性，保留当前外部修改 |
| PERSISTENCE_FAILED | 处理实际存储错误后再次保存 |
| MIGRATION_REQUIRED | 按指定版本和恢复资源执行维护迁移 |

错误正文包含 code、message 和 retryable，可提供 field、action 或 details_resource_id。代际和历史缺口通过 context 返回 current_data_generation、earliest_available_sequence 及 requested_after_sequence 等恢复所需标量。retryable 为 true 表示保留原逻辑请求身份与目标上下文、满足所列条件后可以安全继续；重试仍需满足幂等和状态核对条件。需要修改输入、接受新数据代际或重建消费位置的错误使用 false，并给出建立新请求的动作。PARAMETER_BUSY 与 PLAYBACK_SWITCH_BUSY 在仍使用相同目标、输入和数据代际且占用已释放时可以 retryable 为 true 重试，幂等查询先于忙检查。PARAMETER_CONFLICT 与需重新读取归属或序列的 OUTPUT_CONFLICT 使用 false。冲突回执中的 operation_id 定位既有占用或恢复操作，新的受理身份由成功回执给出；参数冲突详情通过 details_resource_id 读取。错误正文只包含当前操作需要的原因和动作。堆栈、完整上游载荷和鉴权内容留在受限诊断渠道。0、false 和合法空集合按 Schema 保留。

## 通知

事件直接作为 notifications/message 的结构化 data 发送，不嵌套编码成 JSON 字符串。字段见[直播事件](../design/events.md)。

通知发出、客户端收到和 Agent 执行动作分别观察。服务通过事件历史和水位支持补拉；动作分发使用已持久化的事件动作身份去重。业务恢复不依赖传输自动续流。
