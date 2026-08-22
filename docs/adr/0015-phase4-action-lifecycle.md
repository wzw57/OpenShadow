# ADR-0015：Phase 4 Action 生命周期与副作用安全边界

- Status: Accepted
- Date: 2026-08-22
- Scope: Phase 4 首个 Action 生命周期切片

## Context

Action 会触发账户、API、设备或其他现实能力，不能沿用普通 Conversation/Task 的成功语义。
必须先持久化可恢复状态，再调用 Provider，并在不确定结果时避免重复副作用。

## Decision

1. Action 使用 `shadow.profile.action` typed Profile；Proposal、Approval、Result 和
   Reconciliation 均使用现有 Canonical record version rows 与 CommitAuthority。
2. Action Proposal 和 Approval Proposal 复用通用 Proposal API，不新增 Proposal 表或 Action 创建路由。
3. 结构化输入必须声明 target、typed parameters、data classification、side effect、capability、
   deadline 和 opaque secret refs；不接受脚本、inline Secret 或未知参数。
4. `none/low` side effect 自动批准，`medium` 需要 Approval Proposal，high-risk 确定性拒绝。
5. Action 状态为 pending、approval_required、approved、executing、succeeded、failed、unknown。
   Provider 调用前必须已经提交 executing；Provider 不能直接 Commit。
6. unknown 只能进入 reconciliation；没有可信证据时保持 unknown，不能盲目 retry。
7. 所有写入执行 Owner/Space、Expected-Version、Capability、deadline 和 idempotency 校验；跨
   Proposal/Action 的变化必须原子提交。
8. 首片只实现确定性 Provider Adapter 和 contract-level verification，不连接真实 Provider、读取
   Secret 或实现 Outbox、Router、Pulse、跨组件 Erasure/Backup。

## Consequences

- Action 的稳定事实、版本、审计和恢复语义由 Shadow 保持；Provider 只负责执行和返回结果。
- low-risk 自动化可用，medium-risk 明确停留在 approval_required；高风险自动化不会被首片误放行。
- unknown 可能长期存在，但用户不会看到未经证实的 succeeded/failed。
- 后续 Outbox、Router、Pulse、Erasure 和 Backup 必须分别建立设计闸门，不得从本 ADR 推断为已实现。

## Revisit When

- 需要新增 cancelling/cancelled 或补偿语义；
- 需要允许高风险 Action 或真实 Provider；
- 需要改变 Approval、Outbox 或 CapabilityEnvelope 的事实所有权；
- 需要引入跨组件 Erasure、Backup 或多用户 Trusted Device。
