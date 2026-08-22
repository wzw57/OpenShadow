# Phase 4 Action & Proactivity 完成状态

状态：**已实现 / 已合并**

## 已完成切片

- Action Profile：Proposal、Approval、low/medium/high policy、Provider Result、unknown
  reconciliation、restart/CAS/idempotency；
- Durable Outbox：Intent、lease、delivery result、unknown reconciliation、dedup、Store outage；
- Router/Policy：PolicyDecision、BindingProposal、namespaced open-world target、Core 最终
  capability/data scope/budget/side-effect/approval/expiry/revocation 检查；
- Semantic Pulse：Trigger/Observation/Proposal、budget/deadline/cooldown/evidence、Admission
  重入、source-unavailable 和禁止直接 Commit；
- 跨组件 Erasure/Backup Metadata：ErasureRequest、quiesce/erase 状态、失败/恢复/幂等、
  Tombstone anti-resurrection、加密 Export metadata 和排除 Secret/Provider 私有状态声明。

## Phase 4 退出条件证据

- 未持久化 Action/Outbox Intent 不执行 Provider；
- unknown outcome 不盲目 retry，必须 evidence-backed reconciliation；
- Policy Engine 不能直接签发 Capability，Router 不能直接 Commit；
- Pulse work-bearing Proposal 必须重新进入 Admission；
- Store outage 不声称现实副作用、Erasure 或 Backup 已完成；
- Outbox 不是通用 Queue/Event Bus，Erasure 不是跨 Store 事务平台；
- 所有新增 Profile Contract 都有 offline Schema、fixtures、同步测试和 restart/failure 证据。

## 明确不在 Phase 4

- 真实外部 Provider、Secret vault、模型 Router 或 Event Stream；
- 通用 Policy Language、Workflow、Queue/Event Bus、后台 Job Platform；
- 加密设备 Backup 内容、密钥托管和 Backup restore execution；
- 真实跨组件删除编排之外的外部原始来源清除；
- Phase 5 多 Endpoint、多用户 ACL、远程 Store 和设备同步。

全量合并闸门：`pytest -q` 224 passed，Ruff、隔离 SQLite Alembic upgrade/downgrade 和
`git diff --check` 均通过。Phase 5 必须从独立设计闸门开始，不得把上述未实现项偷渡为已完成。
