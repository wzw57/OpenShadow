# OpenShadow 领域模型

- 状态：Stage 3 初稿
- 输入：[关键用例](use-cases/README.md)与[责任矩阵](responsibility-matrix.md)
- 目标：冻结最小领域对象、关系、聚合边界和一致性规则
- 非目标：不定义数据库表、ORM、API Payload、进程边界或具体组件

## 1. 建模规则

1. 只有需要稳定身份、长期引用、权威状态或迁移语义的概念进入 Canonical Model。
2. Proposal 与已接受状态分离；外部组件不能直接构造权威对象。
3. Aggregate Boundary 表示一致性和并发边界，不表示数据库表或微服务。
4. 聚合之间只保存 Stable ID / Version Reference，不嵌入另一个聚合的完整状态。
5. Runtime、Model、Memory Engine、Runner 和 Provider 私有状态不进入 Canonical Model。
6. Embedding、Index、Graph、Projection Cache、Prompt Rendering 和 UI Cache 属于 Derived State。
7. 所有 Canonical Record 共享治理信封，但保留强类型 Payload。
8. 删除、迁移、未知结果和来源失效必须显式建模，不能用空值代替。

## 2. 对象分类

### 2.1 Aggregate Root

| Aggregate Root | 负责的一致性边界 |
|---|---|
| Principal | User 或未来服务主体的稳定身份 |
| Space | 资产归属和未来共享边界 |
| InteractionEndpoint | 设备配对、信任和撤销 |
| Conversation | 有序交互、保留策略和单前台 Run 约束 |
| Request | 被接受输入的不可变准入事实 |
| Run | 顶层运行、Attempt、Binding 与生命周期 |
| DurableTask | 跨 Session、Target、重启和等待条件的工作承诺 |
| Memory | Canonical Memory 的版本、来源、纠正和删除 |
| WorldStateProjection | 一个状态键的 accepted value、冲突和 freshness |
| CapabilityAsset | Skill、Executable、Extension、Profile 等长期能力身份 |
| Integration | 已配置外部连接、权限、Secret Reference 和健康 |
| Action | 一个现实副作用的授权、执行和 reconciliation |
| Schedule | 确定性时间触发规则 |
| PortabilityJob | Export、Backup、Import 或 Migration 的一次工作 |
| ErasureRequest | 一次跨组件物理清除意图和完成状态 |

### 2.2 独立 Canonical Record

以下对象需要稳定引用，但不一定各自形成复杂聚合：

- AdmissionRecord；
- Message；
- Observation；
- Artifact；
- EvidenceReference；
- RoutingRule；
- Policy；
- AdapterDescriptor；
- TargetDescriptor；
- StoreBinding；
- SecretReference；
- Tombstone；
- Audit / Usage summary。

### 2.3 Proposal

Proposal 在被 Core 接受前不是权威状态：

- RouteProposal；
- MemoryCandidate；
- WorldStateProposal；
- DurableTaskProposal；
- ActionProposal；
- CompletionProposal；
- ClarificationProposal；
- CapabilityExpansionProposal。

Proposal 可以按审计和 Retention Policy 保存，但不能被外部组件伪装成已提交对象。

### 2.4 Value Object

- StableId；
- Version；
- OwnerRef；
- SpaceRef；
- SchemaRef；
- DataClassification；
- RetentionPolicyRef；
- Provenance；
- EvidenceRef；
- TimeRange / Deadline / TTL；
- CapabilityRef；
- BindingRef；
- Budget；
- IdempotencyKey；
- Checksum；
- Cursor；
- ExpectedVersion；
- FailureClass；
- ExternalReference。

### 2.5 Derived State

- Embedding；
- Vector / Full-text Index；
- Memory Graph；
- Ranking / Routing score；
- Summary Projection；
- Prompt / Context Rendering；
- Runtime Planner / Subtask Graph；
- Model cache；
- UI cache；
- Materialized query view；
- Telemetry backend state。

删除 Derived State 不得导致 Canonical Asset 丢失。

## 3. 关系总图

~~~mermaid
classDiagram
    class Principal
    class Space
    class InteractionEndpoint
    class Conversation
    class Message
    class AdmissionRecord
    class Request
    class Run
    class ExecutionAttempt
    class ExecutionBinding
    class CapabilityEnvelope
    class DurableTask
    class Memory
    class EvidenceReference
    class Observation
    class WorldStateProjection
    class CapabilityAsset
    class Integration
    class Action
    class Schedule
    class PortabilityJob
    class ErasureRequest

    Principal "1" --> "*" Space : controls
    Principal "1" --> "*" InteractionEndpoint : pairs
    Space "1" --> "*" Conversation : contains
    Conversation "1" --> "*" Message : orders
    Message "0..1" --> "1" Request : submits
    AdmissionRecord "0..1" --> "0..1" Request : accepts
    Request "1" --> "1" Run : creates
    Run "1" --> "*" ExecutionAttempt : retries
    Run "1" --> "*" ExecutionBinding : uses
    ExecutionBinding "1" --> "1" CapabilityEnvelope : constrained_by
    DurableTask "1" --> "*" Run : continues_through
    Memory "*" --> "*" EvidenceReference : supported_by
    Observation "*" --> "1" WorldStateProjection : informs
    WorldStateProjection "*" --> "*" EvidenceReference : explains
    CapabilityAsset "*" --> "*" Integration : binds
    Run "0..1" --> "*" Action : proposes
    Schedule "1" --> "*" Run : triggers
    ErasureRequest "*" --> "*" Memory : erases
    ErasureRequest "*" --> "*" Conversation : erases
    PortabilityJob "*" --> "*" Space : scopes
~~~

图中关系表示领域引用，不代表对象必须在同一数据库或进程。

## 4. Canonical Envelope

所有 Canonical Record 至少包含：

~~~text
CanonicalEnvelope
├─ record_id
├─ record_type
├─ schema_ref
├─ owner_ref
├─ space_id
├─ created_by
├─ data_classification
├─ provenance
├─ version
├─ retention_policy
├─ lifecycle_state
├─ created_at / updated_at
└─ typed_payload
~~~

约束：

- owner_ref 可以指向 Principal 或 Space；
- created_by 不等于 owner_ref；
- 无法确定 classification 时使用 sensitive；
- Expected Version 用于并发写入；
- Payload 由 record_type 和 schema_ref 解释；
- Secret 内容不进入普通 Envelope；
- erased 内容只留下不含敏感原文的最小 Tombstone。

## 5. Interaction 聚合

### 5.1 InteractionEndpoint

持有：

- endpoint_id；
- principal_id；
- display_name；
- endpoint_type；
- trust_level：standard / trusted；
- lifecycle；
- paired_at / last_seen_at；
- credential_ref；
- cache_policy；
- revocation metadata。

不持有：

- 浏览器具体 Storage；
- TLS 私钥实现；
- 音频引擎状态。

### 5.2 Conversation

持有：

- conversation_id；
- owner_ref / space_id；
- ordered Message refs；
- active_foreground_run_id；
- retention / classification；
- lifecycle；
- expected_version。

不持有：

- Run 完整内容；
- Canonical Memory；
- Runtime Session。

不变量：

- 同一 Conversation 同时最多一个 foreground generating Run；
- Message 有稳定顺序；
- 过期版本写入被拒绝；
- 删除 Conversation 不自动删除独立 Memory；
- 移动 Space 必须重新校验数据和权限边界。

### 5.3 Message

Message 是不可变交互记录。修正通过新 Message 或 redaction / erase marker 表示，不原地覆盖审计事实。

Message 可以引用 Request、Run、Artifact 和 Memory Candidate，但不拥有它们。

## 6. Admission、Request 与 Run 聚合

### 6.1 AdmissionRecord

AdmissionRecord 表示输入的准入判断：

- source / endpoint；
- received_at；
- decision：accepted / rejected / duplicate / rate_limited；
- safe_reason；
- restricted_reason_ref；
- idempotency key；
- retention metadata。

Rejected Admission 不创建 Request 或 Run。

### 6.2 Request

Request 是被接受输入的不可变事实：

- request_id；
- admission_ref；
- actor / owner / space；
- normalized intent reference；
- conversation / trigger reference；
- classification；
- accepted_at。

一个 Request 恰好创建一个 Root Run。

### 6.3 Run

Run 持有：

- run_id / request_id / optional task_id；
- lifecycle；
- requirements；
- current Binding ref；
- Attempt refs；
- result / failure summary；
- Usage summary；
- cancellation state；
- created / started / ended timestamps；
- expected_version。

ExecutionAttempt 是 Run 聚合内的 Entity：

- attempt_id；
- target / binding version；
- status；
- started / ended；
- failure class；
- Usage；
- result ref；
- external refs。

不变量：

- 重试只能追加 Attempt；
- 已结束 Attempt 不可覆盖；
- completed / failed / cancelled / cancellation_unknown 是终态；
- 用户请求取消先进入 cancelling；
- Run completed 不自动完成 DurableTask；
- Runtime 私有 Subtask 不进入 Run 聚合。

Ephemeral Run 是 Store 故障期间的内存态运行，不是 Canonical Run，不使用 CanonicalEnvelope，也不能产生长期状态或现实副作用。

## 7. Execution Binding 与 Capability Envelope

ExecutionBinding 记录一次实际 Target 选择：

- binding_id / version；
- target descriptor ref；
- capability set；
- data boundary；
- cost / latency / locality constraints；
- route decision provenance；
- fallback policy；
- health snapshot ref。

CapabilityEnvelope 记录该 Binding 获得的授权：

- envelope_id；
- run / task scope；
- allowed capabilities；
- resource / data scope；
- side-effect level；
- budget；
- valid_until；
- component constraints；
- policy version；
- revocation state。

它们可以作为 Run 引用的独立 Canonical Record，也可以在 Stage 3 后续根据一致性需求决定是否并入 Run 聚合。无论物理实现如何：

- Router 只产生 Proposal；
- Binding 由 Core 提交；
- Envelope 不能被 Target 扩大；
- DurableTask 恢复时重新验证 Envelope；
- 跨边界调用形成 Usage 或 Action。

## 8. DurableTask 聚合

持有：

- task_id；
- owner_ref / space_id；
- goal；
- completion criteria；
- lifecycle；
- semantic checkpoint；
- Runtime checkpoint refs；
- related Run refs；
- Artifact refs；
- trigger / waiting condition refs；
- deadline / retry policy；
- current Binding ref；
- completion / failure commit；
- expected_version。

不变量：

- Task 由用户直接创建，或由 Core 接受 TaskProposal 后创建；
- 一个 Task 可以产生多个 Run；
- Runtime Session 不能成为唯一事实源；
- Runtime 只能提出 CompletionProposal；
- unknown Action 未 reconciliation 时不能自动完成；
- Runtime-native Checkpoint 不兼容时可退回 Semantic Checkpoint。

## 9. Memory 聚合

持有：

- memory_id；
- claim / content；
- owner_ref / space_id / scope；
- classification；
- provenance；
- Evidence refs；
- source_dependency；
- validity；
- version / supersedes；
- lifecycle；
- retention；
- erase marker。

不变量：

- MemoryCandidate 不是 Memory；
- Memory Intelligence 不能直接写入；
- correction 创建新版本并 supersede 旧版本；
- dependent 来源失效时 Memory 必须失效或删除；
- unknown 来源依赖进入 review；
- logically deleted 不参与 Recall；
- erased 内容不能由旧 Candidate 复活；
- Index / Embedding / Graph 可重建。

## 10. WorldStateProjection 聚合

建议以状态键作为聚合边界：

~~~text
StateKey
    = owner_ref
    + space_id
    + subject_ref
    + property
    + schema_ref
~~~

持有：

- state_key；
- accepted value；
- accepted Observation ref；
- conflict Observation refs；
- freshness：fresh / stale / unknown；
- observed_at / received_at / expires_at；
- source availability；
- resolution provenance；
- version；
- retention；
- lifecycle。

Observation 是独立、不可变、按类型 Retention 的 Canonical Record。

不变量：

- Source 只能创建 Observation Proposal；
- Resolver 只能创建 WorldStateProposal；
- Core 提交 Projection；
- 用户明确 Observation 优先但不会永久冻结；
- expires_at 后不得保持 fresh；
- Source 删除后标记 unavailable；
- 最后值和不可信原因可恢复；
- unknown 不等于 null 或不存在。

## 11. CapabilityAsset 与 Integration 聚合

### 11.1 CapabilityAsset

统一身份信封覆盖：

- Skill；
- Executable Asset；
- Extension；
- Runtime / Model / Runner Profile；
- Adapter package metadata。

每种类型使用独立 typed payload，不把它们压成相同语义。

Executable Asset 包含 source ref、version、checksum、I/O Contract、runtime requirements 和 requested permissions。高风险授权绑定版本或 checksum。

### 11.2 Integration

持有：

- integration_id；
- extension / adapter ref；
- owner_ref / space_id；
- configuration metadata；
- permission grants；
- Secret refs；
- Capability / Provider Bindings；
- source status；
- health；
- lifecycle；
- compatibility version。

不变量：

- Secret 内容外置；
- disabled 阻止新 Binding；
- deleted 撤销权限与 Secret Reference；
- 删除 Integration 不自动删除外部原始数据；
- Adapter 更换不改变 Integration identity。

## 12. Action 聚合

持有：

- action_id；
- proposal provenance；
- capability / provider binding；
- normalized parameters ref；
- risk / data classification；
- idempotency key；
- approval state；
- lifecycle；
- external reference；
- result / failure / unknown evidence；
- reconciliation history；
- expected_version。

不变量：

- ActionProposal 不直接执行；
- Provider 执行前必须有持久 pending 状态；
- uncertain delivery 进入 unknown；
- unknown 不得盲目重试；
- cancellation requested 不等于 cancelled；
- 相同 idempotency key 不重复副作用；
- Store 不可用时仅允许预配置 Emergency Outbox Flow。

## 13. Schedule、PortabilityJob 与 ErasureRequest

### 13.1 Schedule

持有确定性时间 / 条件触发定义、next occurrence、last outcome、enabled 和 owner / space。Scheduler 实现外置。

### 13.2 PortabilityJob

使用 kind 区分 export、backup、import、migration，持有 Plan、Manifest、Integrity、Mapping、Compatibility 和 lifecycle。

标准导出与完整备份必须使用不同 kind 和 Policy，不能只靠一个布尔开关。

### 13.3 ErasureRequest

持有：

- erasure_id；
- scope / affected object refs；
- requested_by；
- requested_at；
- erase intent version；
- component statuses；
- backup schedules；
- lifecycle；
- completion evidence；
- Tombstone refs。

Adapter 状态至少支持 pending、scheduled、completed、failed、unreachable。聚合只有在 Policy 所需组件均完成或达到明确例外条件后才能 completed。

## 14. 跨聚合一致性

不要求把所有变化放入一个数据库事务。Core 需要定义：

1. 单聚合使用 Expected Version 防止覆盖；
2. 跨聚合使用稳定 Command / Event ID 和幂等处理；
3. Action 必须先持久 pending，再调用 Provider；
4. Run 与 Task 通过引用和事件最终一致；
5. Memory Commit 与 Index Rebuild 最终一致；
6. Observation Commit 与 Projection Update 可以同事务或通过幂等投影事件完成，具体留给 Store Capability；
7. Erasure 使用长期 Process Manager；
8. Export / Migration 使用可恢复 Job；
9. UI Event Stream 是 Canonical State 的投影，不是事实源；
10. Store restricted mode 阻止需要新 Canonical Commit 的流程。

## 15. 待冻结的关键问题

Stage 3 仍需明确：

1. ExecutionBinding 与 CapabilityEnvelope 是 Run 聚合内 Entity，还是独立 Aggregate Root；
2. Message 内容是 Conversation 聚合内 Entity，还是独立不可变 Record；
3. Observation Commit 与 Projection Update 是否要求原子一致；
4. Memory 的版本链由单一 Memory Aggregate 管理，还是每个版本为独立 Record；
5. Policy、RoutingRule 和 TargetDescriptor 是否需要独立 Aggregate Root；
6. Artifact 是统一 Aggregate Root，还是只作为外部 / Store Reference；
7. Event 是否需要独立通用 Canonical Record，还是只保留领域事件；
8. Task waiting condition 的稳定表达方式；
9. Cross-aggregate Domain Event 的最小信封；
10. 多 Space 未来 ACL 如何兼容，但近期不实现。

这些问题必须根据一致性、并发、迁移和删除需求决定，而不能根据某个数据库的使用习惯决定。
