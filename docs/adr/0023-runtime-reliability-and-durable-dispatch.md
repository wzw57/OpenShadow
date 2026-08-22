# ADR-0023：Runtime Reliability 与 Durable Dispatch

- Status: Accepted (implementation authorized)
- Date: 2026-08-23
- Deciders: OpenShadow maintainers
- Related: ADR-0002、ADR-0014、ADR-0021、ADR-0022

## Context

现有 ConversationService 在同一同步调用中先执行 Runtime，再提交 Admission、Run、
Attempt 和 Message。Provider 超时或 Store 在结果阶段不可用时，Shadow 无法区分
“没有执行”“已执行但结果未知”和“结果已生成但尚未提交”。这会破坏重启恢复、幂等
重放和 UI 对运行状态的诚实表达。

Hermes Adapter 还需要把外部 execution/session reference 与 Shadow Run/Attempt 分离，
以支持事件增量读取和可验证的 resume，而不把 Hermes 私有状态移入 Canonical Store。

## Decision

采用两阶段但无新表的 Commit/CAS 流程：

1. 先由 Shadow Authority 原子持久化 Admission、Request、Run(running)、Attempt
   (dispatching) 及用户消息；
2. 只有初始 Commit 成功后才调用 Runtime Provider；
3. 成功或明确失败通过第二个 CAS CommitPlan 写入结果/失败状态；
4. 超时、断线或结果提交失败保持 `waiting/outcome_unknown` 或 `dispatching`，由
   外部查询或 reconciliation 收敛；
5. 相同 idempotency key 在 Provider 调用前重放已有记录，digest 不匹配返回冲突；
6. Hermes 事件通过 Adapter normalized event/cursor 接口读取，Session ID 只作为
   opaque external reference。

不新增数据库表、通用队列、Provider 直连或工具执行能力。现有 Web UI 只显示稳定的
Run/Message 状态，Token streaming 另行设计。

## Consequences

- Provider 调用前有可恢复的 Shadow Attempt；
- Store outage 不会被 UI 误显示成成功；
- 结果阶段会产生额外 CAS Commit，但保留 Canonical version 和审计边界；
- 需要为现有同步 API 增加 pending/unknown 状态和恢复测试；
- Hermes 原生事件格式仍由 Adapter 隔离，Kernel 不理解 Provider 私有语义。

## Rejected alternatives

1. **继续先调用 Provider 再一次性 Commit**：无法在 crash/timeout 后诚实恢复。
2. **新增 RuntimeJobs/Attempts 表**：重复 Canonical Record 与现有 CAS，扩大 Kernel。
3. **让 Hermes 直接写 Store**：绕过 Shadow Authority、Owner/Space 和版本控制。
4. **未知结果自动 Retry**：可能造成重复现实副作用，违反幂等和安全边界。
