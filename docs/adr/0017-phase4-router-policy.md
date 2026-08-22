# ADR-0017：Phase 4 Deterministic Policy 与 Router Proposal 边界

- Status: Accepted
- Scope: Phase 4 Router / Policy 设计闸门
- Date: 2026-08-22

## Context

Action 和 Outbox 已经需要 capability、data scope、budget、side effect、approval 和 expiry
检查。将这些检查交给 Router 或复杂 Policy Engine 会让外部组件获得权限写入能力，也会把
Tiny Kernel 变成策略平台。因此需要冻结“外部提出、Core 最终检查”的窄边界。

## Decision

1. Policy Engine 只产生可审计的 `PolicyDecision`；它不能直接创建 CapabilityEnvelope、
   ExecutionBinding、Action 或 Canonical Version。
2. Router 只产生 `BindingProposal`；Core 重新验证 descriptor、contract version、capability、
   owner/space、data scope、budget、side effect、approval、expiry、revocation 和健康状态后，
   才能提交 Binding。
3. `target_kind` 使用 namespaced open-world contract。候选 target 的 rank、fallback 或模型
   评分不是授权事实，也不能覆盖 Core 的最终拒绝。
4. 同一 proposal idempotency scope 重放必须复用 stable proposal；不同 digest 返回结构化
   mismatch。Policy/Router unavailable 默认不产生允许结果或现实副作用。
5. 本 ADR 不引入策略 DSL、策略表、评分缓存、通用 Queue/Event Bus、HTTP 路由或 Secret 读取。

## Consequences

- 可替换 Router/Policy 不会成为权限根；Core 继续保持确定性治理；
- 新 target kind 可以通过 descriptor/capability 接入，而无需修改 Kernel enum；
- 复杂评分和策略解释可以外置，但必须把结果降级成受限 Proposal/Decision；
- 未来真实需求若需要持久化 Routing Rule、用户可编辑 Policy 或多租户配额，必须另建 ADR。

## Revisit conditions

出现真实跨 Runtime 路由、用户可审计 Routing Rule 或可测量的 policy evaluation 瓶颈时，
另建 capability-specific 设计，不通过本 ADR 引入通用策略平台。
