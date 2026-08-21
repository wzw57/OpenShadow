# OpenShadow 状态机基线

- 状态：Stage 3 基线 / Stage 4 Profile 修订
- 目标：冻结必须跨组件一致的状态转换
- 非目标：不把每个 Profile 的未来状态全部固化进 Tiny Kernel

## 1. 原则

1. 只有 Shadow Authority 可以提交 Canonical State Transition；
2. External Component 返回 typed Proposal、Result 或 family-specific acknowledgement；
3. Command / Proposal 携带 command_id、expected_version 和 actor / proposer；
4. Profile Validator 校验领域不变量，但不能直接 Commit；
5. unknown、stale 和 cancellation_unknown 是有效状态，不用 failed 或 null 代替；
6. 状态机属于 Kernel Contract 或 Profile Version，不能由数据库状态隐式决定；
7. Profile major change 必须提供语义 Migration；
8. Domain Event 只通知已发生的 Commit，不是事实源。

## 2. 状态机归属

| 状态机 | 归属 |
|---|---|
| Admission / Run / Attempt | KERNEL |
| Adapter lifecycle / health | KERNEL minimum |
| Durable Task | CONTRACT-ONLY + Task Profile |
| Memory | Memory Profile |
| State freshness | State Profile + generic expiry |
| Action | Action safety Contract + Action Profile |
| Integration / Skill install | 对应 Profile |
| OperationJob | portability / erasure implementation |

Tiny Kernel 不为每种 Profile 建立永久 enum switch。Profile Descriptor 声明 lifecycle contract，Kernel 调用对应 Validator。

## 3. Run

~~~mermaid
stateDiagram-v2
    [*] --> created
    created --> queued
    created --> waiting
    queued --> running
    queued --> waiting
    running --> waiting
    waiting --> running
    waiting --> queued
    running --> paused
    paused --> queued
    running --> completed
    running --> failed
    running --> cancelling
    waiting --> cancelling
    paused --> cancelling
    cancelling --> cancelled
    cancelling --> cancellation_unknown
    cancellation_unknown --> cancelled: reconciled
    cancellation_unknown --> completed: reconciled
    cancellation_unknown --> failed: reconciled
    cancellation_unknown --> cancelled: reconciled
    cancellation_unknown --> completed: reconciled
    cancellation_unknown --> failed: reconciled
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
~~~

规则：

- 一个 Accepted Request 创建一个 Root Run；
- Retry 不回退 Run Version，而是追加 Attempt；
- cancel request 只进入 cancelling；
- Target acknowledgement 后才能进入 cancelled；
- 无法确认时进入 cancellation_unknown；
- cancellation_unknown 不是永久终态，后续 reconciliation 可以提交 cancelled、completed 或 failed；
- 没有 cancel Capability 的 Adapter 返回 unsupported，Core 决定是否等待、隔离或标记 unknown；
- completed 不自动完成 Durable Task；
- ephemeral interaction 不是 Canonical Run。

## 4. ExecutionAttempt

~~~mermaid
stateDiagram-v2
    [*] --> created
    created --> dispatching
    dispatching --> running
    dispatching --> rejected
    running --> succeeded
    running --> failed
    running --> outcome_unknown: timeout or lost response
    running --> cancellation_requested
    cancellation_requested --> cancelled
    cancellation_requested --> outcome_unknown
    created --> incompatible
    outcome_unknown --> succeeded: reconciled
    outcome_unknown --> failed: reconciled
    outcome_unknown --> cancelled: reconciled
    rejected --> [*]
    succeeded --> [*]
    failed --> [*]
    cancelled --> [*]
    incompatible --> [*]
~~~

规则：

- Attempt 绑定一个不可变 ExecutionBinding snapshot / reference；
- incompatible 包括 required Capability 或 Contract Version 不满足；
- 未知 target kind 不自动 incompatible，先验证 Descriptor / Capability；
- 终态 Attempt 不可覆盖；
- Retry 创建新 Attempt；
- deadline 超过但无法证明 Target 已停止时进入 outcome_unknown，不能把 timeout 当成已失败；
- outcome_unknown 可以通过 reconciliation 转为 succeeded、failed 或 cancelled；
- 外部 progress 不等于 Canonical lifecycle commit。

## 5. Memory Profile

~~~mermaid
stateDiagram-v2
    [*] --> active
    active --> superseded
    active --> invalidated
    invalidated --> active: accepted correction
    superseded --> [*]
~~~

Memory 直接使用 Canonical Envelope 的不可变版本，不建立平行的 MemoryVersion 或 Root current_version_ref。Correction 创建同一 Memory ID 的新 Version；merge 原子创建新 Memory 并为输入 Memory 提交 superseded Version。logical delete 与 erased 属于 Envelope `record_state`，不与 Profile `memory_state` 混用。

规则：

- MemoryCandidate 在 accepted 前不是 Memory；
- source_dependency 为 dependent 且来源失效时，Profile 决定 invalid / delete / confirmation；
- logical delete 可恢复；
- erased 内容不可恢复；
- 最小 Tombstone 防止旧 Candidate 复活；
- 敏感内容可以擦除旧 Version payload；
- Memory Intelligence 不提交状态。

## 6. Durable Task Profile

~~~mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> active: Shadow accepts
    proposed --> rejected
    active --> waiting
    waiting --> active
    active --> paused
    paused --> active
    active --> completion_pending
    completion_pending --> completed: Shadow commits
    completion_pending --> active: rejected
    active --> cancelling
    waiting --> cancelling
    paused --> cancelling
    cancelling --> cancelled
    cancelling --> cancellation_unknown
    active --> failed
    rejected --> [*]
    completed --> [*]
    cancelled --> [*]
    failed --> [*]
~~~

规则：

- proposed 可以是短期 Proposal，不一定长期保存；
- accepted 后才产生 Canonical Task Record；
- Runtime 只能提交 CompletionProposal；
- Task 可以关联多个 Run；
- Task 完成条件由 Profile 定义；
- unknown Action 未 reconciliation 时不能自动 completed；
- Workflow 私有节点不进入 Task State；
- Kernel 只保证 stable identity、refs 和 completion commit。

## 7. State Profile Freshness

~~~mermaid
stateDiagram-v2
    [*] --> unknown
    unknown --> fresh: accepted state proposal
    fresh --> fresh: newer accepted version
    fresh --> stale: expires_at reached
    fresh --> stale: source unavailable
    stale --> fresh: accepted refresh
    stale --> unknown: no usable evidence
    unknown --> fresh: accepted observation
    fresh --> deleted: user erase
    stale --> deleted: user erase
    unknown --> deleted: user erase
    deleted --> [*]
~~~

规则：

- Freshness 是 State Profile 语义，不是所有 Canonical Record 的生命周期；
- Kernel 可以提供 generic expires_at scheduler / validation；
- expires_at 后不得保持 fresh；
- null 不代替 unknown；
- 用户陈述优先级属于 Profile source policy，不进入 Kernel；
- Resolver 只提交 StateProposal；
- 删除 Integration 后 source unavailable，按 Profile 进入 stale / unknown；
- Accepted State 可恢复和迁移，但允许过期。

## 8. Action Profile

~~~mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> approval_pending
    proposed --> pending: deterministic approval
    approval_pending --> pending: approved and persisted
    approval_pending --> rejected
    pending --> executing
    executing --> succeeded
    executing --> failed
    executing --> unknown
    unknown --> succeeded: reconciliation
    unknown --> failed: reconciliation
    unknown --> unknown: still unresolved
    rejected --> [*]
    succeeded --> [*]
    failed --> [*]
~~~

规则：

- ActionProposal 与 Action 分离；
- Provider 调用前必须持久化 pending；
- approval_pending 不允许调用 Provider；
- 使用 idempotency key；
- timeout 或 connection loss 不自动等于 failed；
- unknown 不盲目 Retry；
- reconciliation 可以由 Provider Capability 执行；
- Store 不可用且没有可靠 Outbox 时不能进入 executing。

## 9. Adapter 与 Binding 生命周期

Adapter lifecycle：

~~~text
discovered → installed → enabled
                        ├─ disabled
                        ├─ incompatible
                        └─ removed
~~~

Health 独立：

~~~text
unknown ↔ healthy ↔ degraded ↔ unavailable
~~~

规则：

- health 变化不直接删除 Adapter；
- Binding 使用明确 Adapter / version / capability snapshot；
- 升级需要 compatibility、Contract Test、可选 migration 和 canary；
- Adapter 不得宣称未实现 Capability；
- removed Adapter 的历史 Binding ref 继续可审计。

## 10. SkillAsset Profile

安装生命周期：

~~~text
discovered → validated → installed → enabled
                  └────→ rejected
enabled ↔ disabled
installed → update_available → validated
installed / disabled → removed
~~~

规则：

- validated 检查 Agent Skills Bundle 和 digest；
- Shadow governance metadata 保存在 sidecar Canonical Record；
- Bundle 不被修改；
- 高风险权限绑定 digest / revision；
- Provider upload 是 Projection，不改变 Canonical install state；
- `allowed-tools` 不直接产生 CapabilityEnvelope。

## 11. OperationJob

只允许 kind：

- export；
- import；
- migration；
- backup；
- erasure。

~~~text
planned → running → waiting | completed | failed
running / waiting → cancelling → cancelled | cancellation_unknown
cancellation_unknown → cancelled | completed | failed: reconciled
~~~

OperationJob 不用于普通 Memory Maintenance、Workflow、Pulse 或通用后台任务。

## 12. Domain Event

最小 Event Envelope：

~~~text
event_id
event_type
record_ref
record_version
occurred_at
actor_ref
correlation_id
causation_id
payload_schema_ref
typed_payload
~~~

Event 只能描述已经 Commit 的事实或明确的通知状态。Canonical Record 是事实源；普通 Event 可以按 Policy 删除或重建，不要求 Event Sourcing。

## 13. 冻结范围

Stage 4 冻结：

- Run / Attempt 核心状态；
- reconcilable cancellation_unknown / outcome_unknown；
- Memory correction / delete / erase 基础语义；
- Task CompletionProposal / Commit；
- State fresh / stale / unknown；
- Action pending-before-call / unknown / reconciliation；
- Adapter capability honesty；
- Skill Bundle / sidecar 分离；
- OperationJob 窄用途。

后续 Profile 可以增加状态，但：

- 不得改变已发布状态的含义；
- 必须提供兼容与 Migration；
- 不得绕过 Authority；
- 不得把外部私有状态变成唯一事实源。
