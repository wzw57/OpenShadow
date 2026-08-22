# Phase 4 Router / Policy 设计闸门

状态：**Accepted / Phase 4 Router/Policy 获准实现**

本闸门是 Phase 4 的第三个独立切片。它已冻结确定性 Policy Decision 和 Router
BindingProposal 的最小契约并获准实现；不授权实现复杂 Policy Language、自动高风险 Action、真实
Router/Provider 或公开 HTTP 路由。Action 与 Durable Outbox 已合并；Semantic Pulse、
跨组件 Erasure 和 Backup 继续保留为后续独立闸门。

## Authority boundary

- Policy Engine 只能返回 `PolicyDecision`，不能签发 Capability、直接修改 Binding 或写
  Canonical Repository；Core 根据 owner/space、data scope、capability、budget、side effect、
  approval、expiry、revocation 和当前 Adapter health 做最终检查。
- Router 只能返回 `BindingProposal`，不能提交 `ExecutionBinding`、Action 或 Run；Proposal
  必须引用待处理的 Run/Attempt/Task 和候选 Adapter descriptor。
- `target_kind` 保持 namespaced、开放集合；Core 不把候选 target 固定为永久 enum。未知
  target 只有在 Descriptor、Contract Version、Capability 和 Policy 最终检查全部通过时才可接受。
- Router 不得扩大请求的 data scope、capabilities、budget 或 allowed side effects；降级、
  fallback 和不确定性必须显式写入 proposal，不得隐式越权。

## Frozen contracts

`PolicyDecision` 必须包含 decision、policy_ref/version、evaluated_at、effective_until、
allowed capabilities、data scope、resource scope、budget limits、allowed side effects、
approval refs 和 revocation state。Decision 只是一项可审计输入，不等价于最终授权。

`BindingProposal` 必须包含 proposal_id、subject ref、target_kind、adapter_ref、contract
version、required capabilities、requested data scope、policy_decision_ref、candidate rank、
fallback flag、proposed_at 和 idempotency key。它不包含 Secret 原文、Provider 私有状态或
未经验证的执行凭据。

所有 proposal 输入携带 owner/space、expected version（当更新既有 Run/Attempt/Task 时）
和 idempotency key。相同 key + digest 重放返回稳定 proposal；不同 digest 返回
`shadow.repository.idempotency-mismatch`。本切片不新增 Proposal 表或 Router HTTP endpoint。

## 结构化拒绝

至少冻结以下错误：`shadow.policy.denied`、`shadow.policy.scope-expansion`、
`shadow.policy.capability-missing`、`shadow.policy.expired`、`shadow.router.target-unsupported`、
`shadow.router.binding-invalid`、`shadow.router.unauthorized`、`shadow.repository.unavailable`。
Policy/Router unavailable 时不得伪造允许、Binding 或执行成功；Core 可按显式静态规则拒绝，
不能默默扩大权限。

## Design-only 禁止事项

- 不新增通用 Policy Language、规则 DSL、策略数据库、评分缓存或 Event Bus；
- 不让 Policy Engine 直接签发 Capability，不让 Router 直接 Commit；
- 不把 `target_kind` 固定成封闭枚举，不把候选 rank 当作授权，不在 Router 中读取 Secret；
- 不实现真实模型/Provider/Router 联动；Deterministic Adapter 仅用于 Contract 和拒绝路径。

## 评审与实现闸门

实现必须限定在本文件、[ADR-0017](adr/0017-phase4-router-policy.md)、Schema、fixtures、
documentation-sync 和必要的静态契约测试授权的边界内；`phase4/router-policy-implementation`
分支继续复用现有 Binding/Commit 原语，
并通过全量 pytest、Ruff、Alembic upgrade/downgrade 与 `git diff --check`。
