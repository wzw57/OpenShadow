# 交互与准入用例

> 本文中的 Request 均指 work-bearing Request。Health、只读控制面 Query、已有 Run 事件订阅和内部恢复步骤不创建 Root Run。

## UC-001 普通请求闭环

### 目标

用户通过 Text Chat 提交一个不产生现实副作用的普通请求，Shadow 完成准入、绑定、执行和结果提交。

### Actor

- Primary：当前 User；
- Supporting：Web Client、Interaction API、Shadow Core、Router、Execution Target、Durable Store。

### Trigger

用户在一个 Conversation 中发送 finalized message。

### Preconditions

- User Session 有效；
- Interaction Endpoint 未撤销；
- Conversation 可写且版本有效；
- Primary Store 可用；
- 至少一个符合数据、能力和预算要求的 Target 可用。

### Main Flow

1. Web Client 为提交生成 idempotency key，并发送 Conversation version、message 和客户端上下文。
2. Interaction API 完成身份、Endpoint、Space、数据等级和格式检查。
3. Shadow 将其识别为承载工作的输入，创建 Accepted Request 和唯一 Root Run。
4. Core 建立 Execution Requirements。
5. 低风险且可逆的轻微歧义可以按上下文解析；影响任务本质、费用、隐私或副作用时返回 Clarification Request。
6. Router 或静态规则返回 Route Proposal。
7. Core 校验能力、健康、数据边界、预算和 Policy，提交 Execution Binding。
8. Core 签发 Capability Envelope，并创建 Execution Attempt。
9. Target 执行并返回 Result、Usage 和必要 Proposal。
10. Core 校验结果，提交 Attempt 与 Run 状态。
11. Web 通过可恢复事件流收到进度和最终结果。
12. 普通回答显示在 Conversation 中，但不会自动成为 Canonical Memory。
13. 完整消息和输出按 Conversation Retention Policy 保存；最小 Run 始终保留。

### Alternative / Failure Flow

- 短时间完成时，Web 直接显示结果；超过交互阈值时显示 running 和取消入口。
- transient failure 且满足预算、幂等和 Deadline 时，在同一 Run 下创建新 Attempt。
- Target 失败后，只有存在用户预设路由规则，且不改变数据、费用和任务语义边界时自动换 Target；否则询问用户。
- 无安全 Binding 时返回 Binding Decision Request。
- 用户取消时进入 cancelling；Target 确认后为 cancelled，无法确认时为 cancellation_unknown。
- 用户在运行中发送内容时，必须明确选择补充当前请求、取消并替换或排为下一条消息。

### Durable State Changes

- Accepted Request；
- Root Run；
- Execution Requirements / Binding；
- Capability Envelope reference；
- Execution Attempt summary；
- Usage summary；
- Conversation message reference；
- final Run state。

Prompt、Response 和 Tool Trace 是否持久化由 Retention Policy 决定。Runtime 私有推理不进入 Canonical State。

### External Side Effects

无。模型费用和资源消耗记录为 Usage，不视为现实业务副作用。

### Policy / Privacy

- Model Binding 限制允许的数据等级、Memory、World State 和外部资产内容；
- 无法判断的数据默认 sensitive；
- Context 在发送前最小化；
- Router 和 Target 不能扩大 Envelope；
- 完整执行细节默认折叠，用户可以查看 Binding、Attempt、费用和错误。

### Acceptance Criteria

- 一个 Accepted work-bearing Request 恰好创建一个 Root Run；
- 自动重试不创建第二个 Root Run；
- transient 与 permanent failure 行为可区分；
- Target 切换不突破数据、费用和语义边界；
- 普通回答不自动成为 Memory；
- 页面刷新或换设备后仍能恢复 Canonical Run 状态；
- Runtime 私有规划不需要被 Shadow 持久化。

## UC-002 请求拒绝、重复提交与降级

### 目标

Shadow 在认证、格式、权限、重复、限流或 Store 故障情况下保持一致且可解释的准入行为。

### Actor

- Primary：User、Voice Endpoint 或 Integration；
- Supporting：Interaction API、Admission、Policy Authority、Primary Store。

### Trigger

任意入口提交输入或事件。

### Preconditions

输入到达 Shadow Admission。

### Main Flow

1. Admission 检查来源身份、Endpoint、Request 格式、idempotency key、Policy、并发和 Store 状态。
2. 合法请求进入 UC-001 或相应业务用例。
3. 被拒绝输入只创建受 Retention Policy 控制的最小 Admission Record，不创建 Run。
4. 用户收到可安全公开的拒绝原因和修正方式。
5. 内部 Policy 与安全细节只写入受限记录。

### Alternative / Failure Flow

- 相同 idempotency key 重复提交时，返回已有 Request / Run 状态，不重复执行。
- 没有 idempotency key 时，即使内容相同也视为新意图。
- 超过限流时返回 rate-limited 和 retry-after；只有符合 Queue Policy 的请求才排队。
- hard deny 不可由用户覆盖；approval required 可以由符合条件的 User 和 Device 批准。
- Primary Store 不可用时，可以明确进入 Ephemeral Run：
  - 只存在于当前进程；
  - 不承诺恢复；
  - 不产生 Memory、Task、Artifact 或现实动作；
  - 不自动补写为历史。
- Store 恢复且 Ephemeral Result 仍在当前进程时，用户可以将它显式保存为新的 Artifact 或 Memory Candidate，并保留 degraded-session provenance。
- Voice partial transcript 只是临时交互状态；只有 finalized utterance 进入 Admission。
- 被撤销 Integration 的事件创建最小 revoked-source Admission Record，并更新 Integration 健康或安全状态。

### Durable State Changes

正常可用时：

- Admission Record；
- duplicate / rate-limit / policy decision；
- Integration health / security status；
- Approval Request when applicable。

Store 故障期间无法承诺任何 Canonical Commit。

### External Side Effects

无。Ephemeral Run 禁止现实副作用。

### Policy / Privacy

- Admission Record 使用最小必要内容；
- 安全原因面向用户做安全裁剪；
- rate limit 与模型降级分别处理；
- Ephemeral Result 不能假装成故障期间已经持久化的历史。

### Acceptance Criteria

- 准入失败不创建 Root Run；
- 相同 idempotency key 不重复执行；
- 相同文本但不同提交可创建不同 Request；
- hard deny 与 approval required 可区分；
- Ephemeral Run 不产生长期状态或副作用；
- Voice partial transcript 不创建 Request；
- revoked Integration 不会恢复或启动 Run。

## UC-UI-001 Web 多端连接与继续

### 目标

用户通过本机或局域网 Web 安全访问同一个 Shadow，并在多个设备之间查看和控制一致的 Conversation、Run 和 Task。

### Actor

- Primary：当前 User；
- Supporting：Web Client、Interaction API、Endpoint Registry、Event Stream、Shadow Core。

### Trigger

用户打开 Web、配对新设备、继续 Conversation，或在另一设备控制 Run / Task。

### Preconditions

- Shadow Web 服务可用；
- 本机完成首次初始化；
- 局域网入口使用安全连接或受信任网关。

### Main Flow

1. 本机初始化首个 Trusted Endpoint。
2. 新设备通过明确配对或登录建立 Session。
3. Core 创建或恢复 Interaction Endpoint Record，并标记 Standard 或 Trusted。
4. 用户进入默认 Personal Space，并打开或创建 Conversation。
5. Web 获取 Snapshot 和 event cursor。
6. 后续 Run、Task、Approval 和 Conversation 变化通过有序事件流推送。
7. 断线重连时从 cursor 补取；cursor 失效时重新获取 Snapshot。
8. 多端看到相同 Canonical 状态。
9. 修改 Task 或 Conversation 时提交 expected version；版本过期则拒绝并刷新。
10. 同一 Conversation 同时只运行一个前台生成 Run；后台 Durable Task 独立运行。
11. 用户可以展开查看 Binding、Attempt、费用和错误。

### Alternative / Failure Flow

- Standard Device 可以聊天和查看允许的数据，但高风险 Approval、restricted 数据、完整备份和敏感删除需要 Trusted Device。
- Run 进行中追加内容时，Web 提供补充、取消并替换、排为下一条三种明确操作。
- Endpoint 被撤销后，服务端立即拒绝新请求并要求重新配对。
- 可连接的撤销设备清除受管 Session、凭据和缓存；无法连接时状态保持 pending / unreachable。
- 离线时只允许打开缓存 UI 和查看授权的有限内容，不创建待执行请求。
- Push-to-Talk 只在用户主动录音后提交 finalized utterance；STT / TTS 通过可替换 Adapter。
- 实时流不可用时，Web 可以降级轮询 Canonical Snapshot，但 Runtime 不能直接连接浏览器。

### Durable State Changes

- Interaction Endpoint；
- trust level；
- Session reference；
- Conversation；
- owner_ref / space_id；
- device revocation；
- user UI preference；
- last acknowledged event cursor when policy requires。

Conversation 是官方 typed Profile，不等于 Run、Memory Profile 或 Durable Task Profile。

### External Side Effects

- 建立或撤销设备 Session；
- 浏览器麦克风访问由用户授权；
- 本地缓存写入受设备信任与数据等级限制。

### Policy / Privacy

- Conversation 默认属于 Personal Space，可以显式移动；
- sensitive / restricted 默认不进入浏览器长期缓存；
- Trusted Device 可以选择启用加密的有限缓存；
- Approval 同时校验 Action Risk 和 Device Trust；
- 局域网不允许明文传输登录、语音、Memory 和 Approval 数据。

### Acceptance Criteria

- 新局域网设备未经配对不能访问 Shadow；
- 撤销设备即使旧 Session 未过期也不能提交请求；
- 两台设备看到相同 Run / Task 状态；
- 过期版本操作不能覆盖新状态；
- 事件流断线后可以恢复；
- 同一 Conversation 不产生无序的并行前台回答；
- Offline Mode 不自动执行过时请求；
- Conversation 删除和 Retention 可以独立于 Memory 执行。
