# OpenShadow 状态机基线

- 状态：Stage 3 初稿
- 目标：定义跨组件可观察、可迁移的最小生命周期
- 非目标：不包含 Runtime、Model、Runner、Memory Engine 或 Provider 私有状态

## 1. 通用规则

1. 只有 Shadow Authority 提交状态转换。
2. External Component 返回 Proposal、Result、Acknowledgement 或 Evidence。
3. 所有 Command 携带 command_id、expected_version 和 actor。
4. 终态不能被普通更新重新打开；恢复必须使用显式新 Command 或新对象。
5. unknown、stale、unreachable 和 cancellation_unknown 是有效业务状态，不用 failed 或 null 代替。
6. 状态转换与副作用必须遵守先持久化意图、后执行、再提交结果。
7. Runtime 私有 planning / tooling / subtask 不进入这些状态机。

## 2. Run

~~~mermaid
stateDiagram-v2
    [*] --> created
    created --> queued: binding accepted
    queued --> running: attempt started
    running --> waiting: external wait
    waiting --> running: condition met
    running --> paused: pause confirmed
    paused --> queued: resume requested
    running --> completed: result committed
    running --> failed: terminal failure
    running --> cancelling: cancel requested
    waiting --> cancelling: cancel requested
    paused --> cancelling: cancel requested
    cancelling --> cancelled: target confirms stopped
    cancelling --> cancellation_unknown: cannot confirm
    created --> cancelled: cancel before start
    queued --> cancelled: cancel before start
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
    cancellation_unknown --> [*]
~~~

约束：

- Retry 追加 ExecutionAttempt，不回退 Run 状态历史；
- transient Attempt failure 可以使 Run 继续 running / queued；
- permanent 或预算耗尽才进入 failed；
- cancellation_unknown 需要独立 reconciliation，而不是自动重试。

## 3. ExecutionAttempt

~~~mermaid
stateDiagram-v2
    [*] --> pending
    pending --> executing
    executing --> succeeded
    executing --> failed
    executing --> timed_out
    executing --> outcome_unknown
    pending --> cancelled
    executing --> cancelling
    cancelling --> cancelled
    cancelling --> outcome_unknown
    succeeded --> [*]
    failed --> [*]
    timed_out --> [*]
    outcome_unknown --> [*]
    cancelled --> [*]
~~~

Attempt 是追加式历史。新重试创建新 attempt_id。

## 4. DurableTask

~~~mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running: run started
    running --> waiting: condition registered
    waiting --> queued: condition met
    running --> paused: pause committed
    waiting --> paused: pause committed
    paused --> queued: resume
    running --> completion_pending: completion proposal
    completion_pending --> completed: criteria verified
    completion_pending --> running: criteria not met
    running --> failed: terminal task failure
    waiting --> failed: deadline or terminal failure
    queued --> cancelling: cancel requested
    running --> cancelling: cancel requested
    waiting --> cancelling: cancel requested
    paused --> cancelling: cancel requested
    cancelling --> cancelled: active work resolved
    cancelling --> cancellation_unknown: cannot confirm
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
    cancellation_unknown --> [*]
~~~

TaskProposal 在 accepted 前不是 Task 状态。Run completed 只允许提出 completion_pending，不直接提交 completed。

## 5. Memory

Memory 有两个正交概念：

- knowledge status：active / invalid / superseded；
- lifecycle：present / logically_deleted / erasure_pending / erased。

推荐组合状态机：

~~~mermaid
stateDiagram-v2
    [*] --> active
    active --> superseded: correction or merge
    active --> invalid: dependent source lost
    invalid --> active: evidence restored and validated
    active --> logically_deleted: user delete
    invalid --> logically_deleted: user delete
    superseded --> logically_deleted: erase history requested
    logically_deleted --> active: restore within window
    logically_deleted --> erasure_pending: window expired or immediate erase
    erasure_pending --> erased: required components cleared
    erasure_pending --> erasure_pending: pending or unreachable
    erased --> [*]
~~~

erased 后只有最小 Tombstone，不允许恢复原内容。

## 6. World State Freshness

Freshness 与记录生命周期分离：

~~~mermaid
stateDiagram-v2
    [*] --> unknown
    unknown --> fresh: accepted observation
    fresh --> fresh: newer accepted observation
    fresh --> stale: expires_at reached
    stale --> fresh: refresh accepted
    stale --> unknown: max staleness or source unavailable
    unknown --> fresh: reliable observation accepted
~~~

约束：

- Source unavailable 不一定立即删除最后值；
- stale / unknown 仍保留最后值、时间和原因；
- Resolver 不直接转换状态，只提出 Proposal；
- 删除 Projection 使用 Erasure / lifecycle，不加入 Freshness 状态机。

## 7. Integration

~~~mermaid
stateDiagram-v2
    [*] --> configured
    configured --> connecting: test connection
    connecting --> active: capabilities verified
    connecting --> degraded: partial availability
    connecting --> disabled: validation failed
    active --> degraded: health or capability loss
    degraded --> active: health restored
    active --> disabled: user disable
    degraded --> disabled: user disable
    disabled --> connecting: re-enable
    configured --> deleted: user delete
    disabled --> deleted: user delete
    active --> deleted: revoke and delete
    degraded --> deleted: revoke and delete
    deleted --> [*]
~~~

deleted 是逻辑生命周期终态；物理 metadata 清除通过 ErasureRequest。

## 8. Action

~~~mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> denied: hard deny
    proposed --> approval_pending: approval required
    proposed --> pending: auto approved and committed
    approval_pending --> pending: approved and committed
    approval_pending --> denied: rejected
    approval_pending --> expired: approval expired
    pending --> executing: provider called
    executing --> succeeded: result confirmed
    executing --> failed: not executed or confirmed failure
    executing --> unknown: delivery uncertain
    executing --> cancelling: cancel requested
    cancelling --> cancelled: provider confirms stopped
    cancelling --> unknown: cannot confirm
    unknown --> succeeded: reconciliation
    unknown --> failed: confirmed not executed
    unknown --> unknown: still unresolved
    denied --> [*]
    expired --> [*]
    succeeded --> [*]
    failed --> [*]
    cancelled --> [*]
~~~

Provider 调用只能发生在持久 pending 之后。unknown 不得被普通 Retry 覆盖。

## 9. InteractionEndpoint

~~~mermaid
stateDiagram-v2
    [*] --> pairing
    pairing --> active_standard: paired
    pairing --> rejected: denied or expired
    active_standard --> active_trusted: trust elevated
    active_trusted --> active_standard: trust reduced
    active_standard --> revoked: user revoke
    active_trusted --> revoked: user revoke
    revoked --> [*]
    rejected --> [*]
~~~

Trust Level 可以单独建模为 Value Object；这里展示其用户可观察转换。

## 10. Store Availability

~~~mermaid
stateDiagram-v2
    [*] --> available
    available --> degraded: partial capability loss
    available --> unavailable: health failure
    degraded --> available: verified recovery
    degraded --> unavailable: commit unsafe
    unavailable --> recovering: health restored
    recovering --> available: integrity verified
    recovering --> unavailable: verification failed
~~~

- unavailable / unsafe degraded 进入 restricted mode；
- recovering 期间不开放 Canonical writes；
- 可写恢复必须经过完整性验证。

## 11. ErasureRequest

~~~mermaid
stateDiagram-v2
    [*] --> planned
    planned --> in_progress: erase intent committed
    in_progress --> partially_complete: some components pending
    partially_complete --> in_progress: component returns
    in_progress --> completed: policy requirements satisfied
    partially_complete --> completed: policy requirements satisfied
    in_progress --> blocked: policy cannot progress
    partially_complete --> blocked: required component failed
    blocked --> in_progress: retry or exception approved
    completed --> [*]
~~~

ComponentStatus 独立支持 pending、scheduled、completed、failed、unreachable。

## 12. PortabilityJob

Export、Backup、Import 和 Migration 使用相同顶层生命周期，但各有不同 Payload 和 Policy：

~~~mermaid
stateDiagram-v2
    [*] --> planned
    planned --> validating
    validating --> ready
    validating --> rejected
    ready --> running
    running --> completed
    running --> failed
    running --> paused
    paused --> running
    failed --> running: explicit retry
    rejected --> [*]
    completed --> [*]
~~~

Import / Migration 失败必须回滚或明确记录部分状态，不能静默完成。

## 13. 尚待决定

1. DurableTask 是否需要独立 blocked 状态，还是统一使用 waiting + reason；
2. Run cancellation_unknown 是否允许在 reconciliation 后转为 cancelled / completed，还是终态后创建 Resolution Record；
3. Memory invalid 与 superseded 是否正交；
4. Integration deleted 是否允许在保留期内 restore；
5. Action proposed 是否属于 Action 聚合，还是 ActionProposal 被接受后才创建 Action；
6. Store degraded 的精确定义是否由 Capability Matrix 决定；
7. ErasureRequest 的 Policy Exception 是否需要用户 Approval；
8. Conversation lifecycle 与 Message redaction 状态机；
9. Schedule missed occurrence 的 catch-up / skip 语义；
10. Artifact 生命周期。

这些问题在冻结字段和 Port Contract 前必须解决。
