# OpenShadow 状态机基线

- 状态：Stage 3 收紧版
- 目标：定义真正需要跨组件共享的最小生命周期
- 非目标：不为每个 Record、Adapter 或未来能力创建状态机

## 1. 原则

1. 只有 Shadow Authority 提交 Canonical State Transition。
2. External Component 返回 Proposal、Result、Acknowledgement 或 Evidence。
3. Command 携带 command_id、expected_version 和 actor。
4. unknown、stale 和 cancellation_unknown 是有效业务状态，不用 failed 或 null 代替。
5. Runtime 私有 planning、tooling 和 subtask 不进入 Canonical 状态机。
6. 第一版只实现 MVP-1 状态机；其余状态先作为 Contract 和测试场景。
7. 新状态只有在改变用户可观察行为、恢复语义或权限边界时才加入。

## 2. 实现优先级

| 状态机 | 层级 | 原因 |
|---|---|---|
| Run | MVP-1 | 所有执行的统一生命周期 |
| ExecutionAttempt | MVP-1 | Retry、费用和失败证据 |
| Memory | MVP-1 | 长期资产、纠正和删除 |
| DurableTask | MVP-2 | 跨时间连续性 |
| WorldState Freshness | MVP-2 | 当前状态的时效诚实性 |
| Action | Later | 现实副作用与 unknown outcome |

InteractionEndpoint、Integration、Store、OperationJob 和 Erasure 的生命周期先使用简单枚举与 Command 校验，不在 MVP-1 建立完整状态机。

## 3. Run

~~~mermaid
stateDiagram-v2
    [*] --> created
    created --> queued: binding accepted
    queued --> running: attempt started
    running --> waiting: external wait
    waiting --> running: condition met
    running --> paused: pause confirmed
    paused --> queued: resume
    running --> completed: result committed
    running --> failed: terminal failure
    running --> cancelling: cancel requested
    waiting --> cancelling: cancel requested
    paused --> cancelling: cancel requested
    cancelling --> cancelled: target confirms
    cancelling --> cancellation_unknown: cannot confirm
    created --> cancelled: cancel before start
    queued --> cancelled: cancel before start
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
    cancellation_unknown --> [*]
~~~

MVP-1 可以先不实现 waiting 和 paused 的用户操作，但必须保留枚举兼容性。

不变量：

- Retry 不创建第二个 Root Run；
- completed、failed、cancelled 和 cancellation_unknown 是终态；
- cancel requested 不等于 cancelled；
- Run completed 不自动完成 DurableTask；
- Ephemeral Run 不进入该 Canonical 状态机。

## 4. ExecutionAttempt

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

Attempt 是 Run 聚合内的追加式 Entity：

- 新 Retry 创建新 attempt_id；
- 已结束 Attempt 不可覆盖；
- transient Attempt failure 不必使 Run failed；
- permanent failure、预算耗尽或无可用 Target 才终止 Run；
- MVP-1 至少实现 pending、executing、succeeded、failed、timed_out。

outcome_unknown 在 MVP-1 主要用于无法确认 Target 结果；涉及现实副作用时由 Later Action 状态机处理。

## 5. Memory

Memory 使用稳定 Root 和不可变 MemoryVersion。状态机只管理 Root 生命周期：

~~~mermaid
stateDiagram-v2
    [*] --> active
    active --> invalid: dependent source lost
    invalid --> active: evidence restored
    active --> logically_deleted: user delete
    invalid --> logically_deleted: user delete
    logically_deleted --> active: restore in window
    logically_deleted --> erasure_pending: erase requested
    erasure_pending --> erased: required copies cleared
    erased --> [*]
~~~

版本变化不作为 Root 状态：

~~~text
Memory.current_version_id
    v1
     ↓ correction
    v2 supersedes v1
     ↓ correction
    v3 supersedes v2
~~~

MVP-1 必须实现 active 和新版本 correction。logical delete 可以先实现；跨组件 erasure_pending / erased 在 Later 完整实现。

约束：

- superseded Version 默认不参与 Recall；
- erased 内容不可恢复；
- dependent 来源失效进入 invalid；
- unknown source dependency 进入 review flag，而不是新生命周期状态；
- Index / Embedding / Graph 不影响 Root 生命周期。

## 6. DurableTask

MVP-2：

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
    running --> failed: terminal failure
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

不增加 blocked。无法继续时使用 waiting + structured reason。

TaskProposal 在 accepted 前不是 Task。Runtime 只能提出 CompletionProposal。

## 7. World State Freshness

MVP-2。Freshness 与删除生命周期分离：

~~~mermaid
stateDiagram-v2
    [*] --> unknown
    unknown --> fresh: observation applied
    fresh --> fresh: newer observation
    fresh --> stale: expires_at reached
    stale --> fresh: refresh applied
    stale --> unknown: max staleness or source unavailable
    unknown --> fresh: reliable observation
~~~

Observation 与 Projection 使用可恢复流程：

~~~text
Observation committed
    → pending_resolution
    → Projection updated
    → Observation applied
~~~

约束：

- Projection 不引用未提交 Observation；
- Resolver 只提出 Proposal；
- expires_at 后不得保持 fresh；
- stale / unknown 保留最后值、时间和原因；
- 删除 Projection 使用 OperationJob / Erasure，不加入 Freshness 状态机。

## 8. Action

Later。ActionProposal 通过校验后才创建 Action：

~~~mermaid
stateDiagram-v2
    [*] --> approval_pending
    [*] --> pending
    approval_pending --> pending: approved and committed
    approval_pending --> denied: rejected
    approval_pending --> expired: approval expired
    pending --> executing: provider called
    executing --> succeeded: confirmed
    executing --> failed: confirmed failure
    executing --> unknown: uncertain delivery
    executing --> cancelling: cancel requested
    cancelling --> cancelled: provider confirms
    cancelling --> unknown: cannot confirm
    unknown --> succeeded: reconciliation
    unknown --> failed: confirmed not executed
    denied --> [*]
    expired --> [*]
    succeeded --> [*]
    failed --> [*]
    cancelled --> [*]
~~~

Provider 调用只能发生在持久 pending 后。unknown 不得盲目 Retry。

## 9. 简单生命周期枚举

以下对象第一版不需要完整状态机：

| Record | 最小枚举 | 实现层级 |
|---|---|---|
| InteractionEndpoint | active / revoked | MVP-2 扩展 trust |
| Integration | configured / active / degraded / disabled / deleted | MVP-2 |
| StoreBinding | available / unavailable / recovering | MVP-1 health check |
| OperationJob | planned / running / completed / failed | Contract-only |
| ComponentEraseStatus | pending / scheduled / completed / failed / unreachable | Later |
| RoutingRule | active / disabled | Later |
| Schedule | enabled / disabled | MVP-2 |

如果未来需要更复杂转换，应由真实失败用例和并发需求证明，而不是提前扩展。

## 10. Domain Event

状态转换产生最小 Domain Event：

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

MVP-1 使用模块化单体内的提交后分发，不要求 Event Sourcing、Broker 或分布式事务。

要求：

- UI Event Stream 消费事件投影；
- Adapter 不直接伪造 Aggregate Version；
- Handler 幂等；
- 重要长期事件按 Policy 持久化；
- Canonical Aggregate 仍是事实源。

## 11. Stage 3 冻结范围

Stage 3 只需正式冻结：

1. Run 状态机；
2. ExecutionAttempt 状态机；
3. Memory Root 生命周期与不可变版本语义；
4. DurableTask 和 WorldState 的 MVP-2 Contract；
5. Action 的 Later Contract；
6. 简单 Record 的最小生命周期枚举；
7. Domain Event Envelope。

Endpoint 配对、Integration 恢复、Store 抖动、Erasure 例外、Schedule catch-up 和 Artifact 生命周期留到相应实现阶段，不阻塞 Stage 4。
