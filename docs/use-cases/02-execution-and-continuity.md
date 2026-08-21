# 执行与连续性用例

## UC-003 直接 Model Worker 执行

### 目标

Shadow 对分类、提取、摘要等受限任务直接调用 Model Worker，不启动 Agent Runtime。

### Actor

User 或内部受授权流程；Shadow Core；Router；Model Adapter。

### Trigger

Accepted Request 的 Execution Requirements 可以由一次受限推理满足。

### Preconditions

- Model Descriptor 与 Model Binding 有效；
- 输入已完成 Data Classification 和 Context 裁剪；
- 预算、地域、Retention 和 Training Policy 允许调用。

### Main Flow

1. Core 根据 Request 创建 Root Run 和 Requirements。
2. 静态规则或 Router 提出 Model Worker Binding。
3. Core 校验模型能力、数据边界、预算和健康。
4. Core 签发只允许单次推理和指定输出 Schema 的 Envelope。
5. Model Adapter 执行并返回 Result 与 Usage。
6. Core 校验输出 Schema，提交 Attempt 和 Run。
7. Result 返回 Conversation；需要长期状态时另行形成 Candidate。

### Failure Flow

- transient timeout 在同一 Run 下创建新 Attempt；
- 输出不符合 Schema 时可在预算内重试一次修复，或返回 structured-output failure；
- 无合规 Model 时询问用户，不自动发送给权限更宽的远程模型；
- Model 返回的 Memory、State 或 Task 内容只能作为 Proposal。

### Durable State Changes

Request、Run、Binding、Attempt summary、Usage 和 Result reference。模型 Prompt 和原始输出按 Retention Policy 保存。

### External Side Effects

模型费用和 Provider Usage；无现实业务副作用。

### Acceptance Criteria

- 不启动 Agent Runtime；
- Model 无权直接提交 Memory、World State 或 Task；
- 不合规模型不能接收超出 Binding 的数据；
- 重试和费用可以追踪。

## UC-004 Executable Asset 与 Runner

### 目标

Shadow 执行一个已登记脚本、函数或固定程序，并保持身份、版本、权限和结果可追踪。

### Actor

User、Schedule、Runtime 或 Semantic Pulse；Shadow Core；Runner Adapter。

### Trigger

Accepted Request 或已授权 Trigger 指向 Executable Asset。

### Preconditions

- Asset Stable ID、版本、checksum 和 I/O Contract 有效；
- Runner 满足 runtime requirements；
- Capability Envelope 覆盖输入、资源和副作用；
- 高风险权限仍绑定当前版本或 checksum。

### Main Flow

1. Core 解析 Asset Reference 和目标版本。
2. Core 校验 provenance、trust、compatibility、permissions 和 checksum。
3. Execution Dispatch 绑定 Runner。
4. Runner 在声明的隔离、依赖和资源限制中执行。
5. Runner 返回结构化 Result、Usage、logs reference 和 exit status。
6. Core 校验输出并提交 Attempt。
7. 输出可以保持临时、形成 Artifact，或作为 Memory / State / Action Proposal。

### Failure Flow

- checksum 或版本变化导致高风险授权失效并请求重新批准；
- 依赖缺失、资源超限和 Sandbox 拒绝返回明确 failure class；
- transient infrastructure failure 可以重试；程序确定性失败不盲目重试；
- Runner 崩溃且无法确认副作用时返回 unknown；
- 未登记的任意代码不能继承 Executable Asset 权限。

### Durable State Changes

Asset identity/version/checksum、Binding、Envelope reference、Attempt、Usage、Artifact / Proposal reference。

### External Side Effects

默认无；声明现实副作用的脚本必须进入 Action 治理路径。

### Acceptance Criteria

- 相同 Stable ID 的高风险代码变化后旧授权不可继续；
- Runner 可替换且不改变 Asset identity；
- Sandbox、依赖和语言运行时不进入 Core；
- 输出不会绕过 Authority 成为 Canonical State。

## UC-005 Run 晋升为 Durable Task

### 目标

普通 Run 发现工作需要跨 Session、重启、Target 或等待条件继续时，安全创建 Durable Task。

### Actor

User；Runtime、Semantic Pulse 或规则；Shadow Task Authority。

### Trigger

- 用户直接要求长期工作；
- 当前 Run 返回 Durable Task Proposal；
- 工作需要等待时间、Event、外部结果或未来恢复。

### Preconditions

- Proposal 包含目标、完成条件、当前进度、下一步、所需 Capability 和 Evidence；
- Owner、Space、数据等级和 Policy 有效；
- Primary Store 可提交。

### Main Flow

1. User 直接创建，或外部组件提交 Task Proposal。
2. Core 校验是否确有跨边界连续性需求。
3. Core 创建 Durable Task Stable ID 和初始状态。
4. Core 保存 Semantic Checkpoint、Artifact refs、waiting / trigger refs 和初始 Binding。
5. 当前 Run 与 Task 建立来源关系。
6. Task 根据状态进入 queued、running 或 waiting。
7. 后续每次执行创建新的 Run。
8. Runtime 返回 Completion Proposal。
9. Core 根据完成条件、外部结果和 reconciliation 提交 completed。

### Failure Flow

- 仅因耗时较长或使用 Agent Runtime，不自动晋升；
- Proposal 缺少可验证目标或完成条件时拒绝或请求澄清；
- Semantic Pulse 只能提出 Proposal，不能直接创建；
- Store 不可用时禁止创建 Durable Task；
- Run 成功但完成条件未满足时，Task 保持 running / waiting；
- 用户取消 Task 时取消未来调度，并对活动 Run 使用 cancelling 语义。

### Durable State Changes

Task、lifecycle、goal、completion criteria、Semantic Checkpoint、bindings、triggers、related Runs、Artifact refs、completion commit。

### External Side Effects

无直接副作用；Task 中的具体 Action 另行治理。

### Acceptance Criteria

- 一个 Task 可以关联多个 Run；
- Task 不依赖单个 Runtime Session；
- Runtime 无权直接提交 completed；
- 重启后可以根据 Canonical Task 恢复；
- Runtime 私有 Subtask 不自动成为 Shadow Task。

## UC-006 Runtime 故障恢复与 Handoff

### 目标

Agent Runtime 中断、升级或被替换后，Durable Task 仍能恢复，并可切换到另一个 Runtime。

### Actor

Shadow Scheduler / Health；Runtime A；Runtime B；User。

### Trigger

Runtime timeout、lease failure、crash、版本不兼容、用户切换或维护升级。

### Preconditions

- Task 是 Durable；
- Task 有 Semantic Checkpoint；
- Runtime-native Checkpoint 如果存在，只作为可选引用；
- 新 Binding 满足 Capability、数据、预算和版本要求。

### Main Flow

1. Health 通过确定性 Lease / Timeout 发现 Runtime A 不可用。
2. 当前 Attempt 标记 failed 或 unknown，不直接完成 Task。
3. Core 保存最后确认进度和 failure evidence。
4. Core 尝试同 Runtime 恢复：
   - Runtime-native Checkpoint 可用且兼容时恢复高保真状态；
   - 否则使用 Semantic Checkpoint。
5. 需要 Handoff 时，Router 提出 Runtime B。
6. Core 校验新 Binding，并重新签发 Capability Envelope。
7. Runtime B 接收 Task goal、Semantic Checkpoint、Artifacts 和允许上下文。
8. 新 Run / Attempt 开始执行。
9. Task Continuity 保持相同 Task Stable ID。
10. Completion Proposal 经 Core 校验后提交。

### Failure Flow

- Runtime-native Checkpoint 不可读取时不阻塞 Semantic Handoff；
- 没有合规 Runtime B 时进入 waiting 并通知用户；
- Resume 时旧 Envelope 已过期或策略变化，则重新授权；
- 外部 Action outcome unknown 时先 reconciliation，不能重复执行；
- Semantic Checkpoint 不足时请求用户补充，不伪造隐藏推理。

### Durable State Changes

Task、Run / Attempt、Runtime Binding history、Checkpoint refs、failure evidence、waiting reason、new Envelope、completion state。

### External Side Effects

可能恢复模型和工具资源；已有现实动作不得在未完成 reconciliation 前重复。

### Acceptance Criteria

- 删除 Runtime A 不删除 Task；
- Runtime B 不需要 Runtime A 的隐藏思维或 Subtask Graph；
- Task Stable ID 和历史关系保持；
- Checkpoint 不兼容有明确降级路径；
- 故障检测不依赖 LLM；
- unknown Action 不因 Handoff 被重复。
