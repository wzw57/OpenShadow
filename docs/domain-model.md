# OpenShadow 领域模型

- 状态：Stage 3 收紧版
- 输入：[关键用例](use-cases/README.md)与[责任矩阵](responsibility-matrix.md)
- 目标：定义足够小、可长期演进的领域模型
- 非目标：不定义数据库表、ORM、API Payload、进程边界或具体外部组件

## 1. 设计立场

Shadow 的完整产品边界很大，但第一版实现必须小。

本模型遵守：

1. 只把需要稳定身份、权威状态、跨组件引用或迁移语义的概念放入 Canonical Model；
2. 不因未来可能需要就创建独立模块、服务或聚合；
3. Proposal 与已接受状态分离；
4. External Component 不能直接提交权威对象；
5. Runtime、Model、Memory Engine、Runner 和 Provider 私有状态不进入 Canonical Model；
6. Aggregate 是一致性边界，不等于数据库表、模块或微服务；
7. 聚合之间使用 Stable ID 引用，不复制完整对象；
8. Derived State 可以删除重建；
9. 第一版采用模块化单体、一个 Primary Store 和少量 Adapter；
10. 长期兼容性通过 Contract 和 Canonical Record 保留，不要求立即实现所有能力。

## 2. 实现分层

### Phase 0–1：工程基础与个人 Shadow 闭环

必须实现：

~~~text
Local Web
   ↓
Conversation / Message
   ↓
Admission / Request / Run
   ↓
Execution Binding + minimal Capability Envelope
   ↓
One Runtime or Model Adapter
   ↓
Result
   ↓
Memory Candidate / Canonical Memory
   ↓
One Primary Durable Store
~~~

Phase 0–1 不要求立即实现：

- 多用户；
- 完整 Home Space；
- 智能 Router；
- Semantic Pulse；
- 复杂 State Resolver；
- 现实 Action；
- Emergency Outbox；
- 完整 Export / Erasure Process；
- 多 Runtime Handoff；
- 分布式音频；
- 微服务或消息队列。

### Phase 2–3：记忆、能力资产、连续性与 World State

在 Phase 0–1 稳定后分阶段增加：

- Durable Task；
- Minimal World State；
- Integration Registry；
- Multi-device Web；
- Executable Asset / Runner；
- 基础 Export / Import；
- Runtime Handoff。

### Later：高级治理与主动智能

按真实用例增加：

- 外部 Action 与 Reconciliation；
- 完整 Erasure Process；
- Full Device Backup；
- Emergency Outbox；
- 智能 Router；
- Semantic Pulse；
- 多 Space ACL；
- 复杂状态融合；
- 家庭语音 Endpoint。

### Contract-only

以下概念可以先定义最小引用或接口，不开发完整机制：

- Space membership / roles；
- Target scoring；
- Backup engine；
- Erasure component orchestration；
- State Resolver；
- Secret Store implementation；
- Device trust hierarchy；
- Schedule catch-up policy。

## 3. 最小领域分区

| Domain | 核心职责 | 第一版 |
|---|---|---|
| Interaction | Conversation、Message、Endpoint | Conversation / Message |
| Execution | Admission、Request、Run、Attempt、Binding | 必须 |
| Continuity | Durable Task、Checkpoint、Trigger refs | Phase 3 |
| Knowledge | Memory、Observation、World State | Memory Phase 2，World State Phase 3 |
| Capability | Skill、Executable、Integration、Profiles | 最小 Integration / Profile |
| Authority | Policy、Envelope、Approval、Action | 最小 Envelope；Action Later |
| Portability | Store、Export、Erasure、Migration | Store 必须，其余 Contract-only |

这些是逻辑领域，不要求拆成独立进程。

## 4. 最小对象分类

### 4.1 主要 Aggregate Root

最终模型只保留以下主要聚合：

| Aggregate | 作用 | 交付层 |
|---|---|---|
| Conversation | 有序交互与单前台 Run 约束 | Phase 1 |
| Run | 一次顶层执行及其 Attempts | Phase 1 |
| DurableTask | 跨时间工作承诺 | Phase 3 |
| Memory | Canonical Memory 与版本头 | Phase 2 |
| WorldStateProjection | 一个状态键的当前投影 | Phase 3 |
| Integration | 已配置外部连接 | Phase 2 |
| Action | 一个现实副作用 | Later |
| OperationJob | Export、Import、Migration、Backup、Erasure | Contract-only / Later |

不为 Principal、Space、Schedule、Endpoint、CapabilityAsset、Policy、RoutingRule、Descriptor 分别建立复杂聚合，除非真实并发和生命周期证明必要。

### 4.2 独立 Canonical Record

- Principal / Space；
- InteractionEndpoint；
- Message；
- AdmissionRecord；
- Request；
- Observation；
- EvidenceReference；
- Artifact；
- CapabilityAsset；
- ExecutionBinding；
- CapabilityEnvelope；
- RoutingRule；
- Policy；
- Adapter / Target Descriptor；
- StoreBinding；
- SecretReference；
- Schedule / Trigger；
- Tombstone；
- Usage / Audit summary。

这些记录可以有 Stable ID 和 Version，但第一版不需要专属 Repository、Service 或状态机。

### 4.3 Proposal

- RouteProposal；
- MemoryCandidate；
- WorldStateProposal；
- DurableTaskProposal；
- ActionProposal；
- CompletionProposal；
- ClarificationProposal；
- CapabilityExpansionProposal。

Proposal 在被 Core 接受前不是权威状态。是否长期保存由审计和 Retention Policy 决定。

### 4.4 Value Object

- StableId / Version / ExpectedVersion；
- OwnerRef / SpaceRef / SchemaRef；
- DataClassification / RetentionPolicyRef；
- Provenance / EvidenceRef；
- Deadline / TTL / TimeRange；
- CapabilityRef / BindingRef；
- Budget / Checksum / Cursor；
- IdempotencyKey / FailureClass / ExternalReference。

### 4.5 Derived State

Embedding、Index、Memory Graph、Router Score、Summary Projection、Prompt Rendering、Runtime Planner、UI Cache、Materialized View 和 Telemetry Backend State 均为 Derived State。

## 5. 关系总图

~~~mermaid
classDiagram
    class Conversation
    class Message
    class Request
    class Run
    class ExecutionAttempt
    class ExecutionBinding
    class CapabilityEnvelope
    class DurableTask
    class Memory
    class Observation
    class WorldStateProjection
    class Integration
    class Action
    class OperationJob

    Conversation "1" --> "*" Message : orders
    Message "0..1" --> "1" Request : submits
    Request "1" --> "1" Run : creates
    Run "1" --> "*" ExecutionAttempt : appends
    Run "1" --> "*" ExecutionBinding : uses
    ExecutionBinding "1" --> "1" CapabilityEnvelope : constrained_by
    DurableTask "1" --> "*" Run : continues_through
    Observation "*" --> "1" WorldStateProjection : informs
    Integration "1" --> "*" Observation : sources
    Run "0..1" --> "*" Action : proposes
    OperationJob "*" --> "*" Memory : operates_on
    OperationJob "*" --> "*" Conversation : operates_on
~~~

图表示 Stable Reference，不表示数据库外键、同一事务或进程调用。

## 6. Canonical Envelope

所有 Canonical Record 使用共同治理元数据：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ data_classification
├─ provenance / version
├─ retention_policy / lifecycle_state
├─ created_at / updated_at
└─ typed_payload
~~~

第一版要求：

- owner_ref 和 space_id 字段存在；
- 默认只有当前 User 和 Personal Space；
- Home Space 可以预创建但不实现成员 ACL；
- classification 无法判断时为 sensitive；
- ExpectedVersion 防止覆盖；
- Secret 内容不进入普通 Envelope；
- erased 内容只保留最小 Tombstone。

## 7. Interaction

### Conversation Aggregate

持有 conversation_id、有序 Message refs、active_foreground_run_id、owner / space、retention / classification、lifecycle 和 expected_version。

Message 采用已确认方案：

- 独立、不可变 Canonical Record；
- Conversation 只保存有序引用；
- 修正通过新 Message；
- redaction / erase 不原地篡改历史；
- 单条内容可以使用独立 Retention 和 Erasure；
- Message 可以引用 Request、Run 和 Artifact。

不变量：

- 一个 Conversation 同时最多一个 foreground generating Run；
- 过期版本写入被拒绝；
- 删除 Conversation 不自动删除独立 Memory；
- Runtime Session 不属于 Conversation。

Phase 1 只实现 localhost Web 和单 Endpoint。配对、Standard / Trusted、离线缓存和多设备能力进入 Phase 5。

## 8. Execution

### AdmissionRecord 与 Request

AdmissionRecord 是最小准入事实。Rejected / duplicate / rate-limited 不创建 Request 或 Run。

Request 是不可变 Canonical Record。一个 Accepted Request 恰好创建一个 Root Run。

### Run Aggregate

持有 run_id、request_id、optional task_id、lifecycle、requirements、Binding refs、Attempt entities、result / failure / Usage summary、cancellation state、timestamps 和 expected_version。

不变量：

- Retry 只追加 Attempt；
- 已结束 Attempt 不可覆盖；
- completed / failed / cancelled / cancellation_unknown 是终态；
- cancel request 先进入 cancelling；
- Run completed 不自动完成 DurableTask；
- Runtime 私有 Subtask 不进入 Canonical Model。

Ephemeral Run 在 Store 故障期间只存在于内存，不是 Canonical Run，不产生长期状态或现实副作用。

### Binding 与 Envelope

采用已确认方案：

- ExecutionBinding 是独立 Canonical Record；
- CapabilityEnvelope 是独立 Canonical Record；
- Run / Task 使用 Stable Reference；
- 二者可以独立版本、审计、撤销和重新验证；
- Router 只提出 Binding；
- Target 不能扩大 Envelope。

Phase 1 只需静态 Binding 和最小 Envelope：

~~~text
target
allowed_capabilities
data_scope
budget
valid_until
policy_version
~~~

高级 Fallback、评分和长期授权以后增加。

## 9. DurableTask

Phase 3 Aggregate，持有 goal、completion criteria、lifecycle、Semantic Checkpoint、optional Runtime Checkpoint refs、related Run refs、Artifact / Trigger refs、deadline / retry 和 completion commit。

不变量：

- 外部组件只能提交 TaskProposal；
- 一个 Task 可以产生多个 Run；
- Runtime Session 不是事实源；
- CompletionProposal 由 Core 校验；
- unknown Action 未 reconciliation 时不能自动完成。

第一版不需要通用 Workflow Engine 或复杂 Task Graph。

## 10. Memory

采用已确认的版本方案：

- Memory 是稳定 Aggregate Root；
- 每个 MemoryVersion 是独立、不可变 Canonical Record；
- Root 指向 current_version_id；
- correction 创建新版本并 supersede 旧版本；
- 敏感 Erasure 可以删除具体版本内容；
- Root / Tombstone 防止旧 Candidate 复活。

Memory Root 最小字段包括 memory_id、current_version_id、owner / space / scope、validity / lifecycle、source_dependency、retention 和 erase marker。

MemoryVersion 包含 Claim / content、provenance、Evidence refs、classification 和 created_at。

MemoryCandidate 不是 Memory。Embedding、Index 和 Graph 不属于聚合。

## 11. World State

WorldStateProjection 是 Phase 3 Aggregate，以 StateKey 为边界：

~~~text
StateKey
    = owner_ref
    + space_id
    + subject_ref
    + property
    + schema_ref
~~~

Observation 是独立不可变 Record，并使用类型级 Retention。

采用已确认的可恢复两阶段流程：

~~~text
Observation committed
    → pending_resolution
    → Projection updated
    → Observation marked applied
~~~

约束：

- Projection 不能引用未提交 Observation；
- Command / Event 必须幂等；
- Store 支持事务时可以优化为单事务，但 Contract 不强制；
- Resolver 只返回 Proposal；
- expires_at 后不得保持 fresh；
- unknown 是显式状态，不是 null。

复杂 State Resolver、预测和数字孪生不属于 MVP。

## 12. Capability 与 Integration

第一版不建立统一“万能能力聚合”。

CapabilityAsset 使用共同 Envelope + typed payload，覆盖 Skill、Executable、Extension 与 Runtime / Model / Runner Profile。

Integration 作为 Phase 2 Aggregate，持有配置元数据、Permission、Secret Reference、Binding、Health 和 Lifecycle。

Secret 内容外置。Adapter 更换不改变 Integration ID。

## 13. Action 与 OperationJob

### Action

Later Aggregate。采用已确认方案：

- ActionProposal 与 Action 分离；
- Proposal 通过 Schema 和 Policy 后才创建 Action；
- 初始状态是 approval_pending 或已持久化 pending；
- Provider 调用前必须持久化；
- uncertain delivery 进入 unknown；
- unknown 不盲目 Retry。

现实 Action 在 Phase 4 实现。

### OperationJob

为避免 ExportJob、BackupJob、MigrationJob、ErasureJob 各自膨胀，使用一个通用 OperationJob Aggregate：

~~~text
kind
scope
plan
status
progress
component_results
integrity
failure
~~~

kind 可以是 export、import、migration、backup、erasure。每种 kind 使用不同 Schema 和 Policy。

Phase 0–1 建立 Export Contract 与基础导出；复杂 Job Orchestration 在 Phase 3–4 实现。

## 14. Domain Event

采用最小 Domain Event Envelope，但不采用强制 Event Sourcing：

~~~text
event_id
event_type
aggregate_ref
aggregate_version
occurred_at
actor_ref
correlation_id
causation_id
payload_schema_ref
payload
~~~

用途包括跨聚合最终一致、UI Event Stream、Adapter 通知、派生索引重建和审计关联。

Canonical Aggregate 仍是事实源。普通内部通知可以短期保存或重建，只有长期业务事件按 Policy 持久化。

## 15. 跨聚合一致性

1. 单聚合使用 ExpectedVersion；
2. 跨聚合 Command / Event 使用 Stable ID 和幂等处理；
3. Action 先持久 pending，再调用 Provider；
4. Run 与 Task 通过引用最终一致；
5. Memory Commit 与 Index Rebuild 最终一致；
6. Observation 与 Projection 使用可恢复两阶段流程；
7. UI Event Stream 是投影，不是事实源；
8. Store restricted mode 阻止新的 Canonical Commit；
9. OperationJob 管理长时间 Export / Migration / Erasure；
10. Phase 0–1 不引入消息队列；模块化单体可以在提交后同步分发 Domain Event，并保留未来 Outbox 接口。

## 16. 首条实现闭环

Stage 4 和 Stage 5 应围绕这一条路径设计：

~~~mermaid
flowchart LR
    WEB["Local Web"]
    CONV["Conversation / Message"]
    ADMIT["Admission / Request"]
    RUN["Run / Attempt"]
    BIND["Static Binding / Envelope"]
    TARGET["One Runtime or Model Adapter"]
    RESULT["Result"]
    MEM["Memory Candidate / Memory"]
    STORE[("One Primary Store")]

    WEB --> CONV --> ADMIT --> RUN --> BIND --> TARGET
    TARGET --> RESULT --> CONV
    RESULT --> MEM --> STORE
    RUN --> STORE
    CONV --> STORE
~~~

验收重点：

- 重启后 Conversation、Run 和 Memory 可恢复；
- 更换 Target Adapter 不改变 Canonical ID；
- Memory Component 只能提交 Candidate；
- 普通回答不自动成为 Memory；
- Store 不可用时只允许明确 Ephemeral Run；
- 不需要 Router、Pulse、World State、Action 或多用户系统即可运行。

## 17. Stage 3 剩余工作

不再继续扩展候选对象。只需要：

1. 校验上述聚合是否足以覆盖 19 个用例；
2. 冻结 Phase 0–1 对象的最小字段；
3. 冻结 Run 和 Memory 必需状态；
4. 定义最小 Domain Event Envelope；
5. 把 Later / Contract-only 项目明确留到后续；
6. 为 Stage 4 字段级 Port Contract 提供对象引用和一致性要求。

多用户 ACL、复杂 Task、Action、Erasure、Portability、Pulse 和家庭设备细节按 Phase 3–5 实现，不阻塞 Phase 0–1。
