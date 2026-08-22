# ADR-0016：Phase 4 Durable Outbox 最小可靠副作用边界

- Status: Proposed
- Scope: Phase 4 Durable Outbox 设计闸门
- Date: 2026-08-22

## Context

Action 已有 `executing`/`unknown` 生命周期，但跨边界 Provider 调用需要在 Store 故障、
进程重启和重复投递下保留可恢复意图。引入通用 Queue/Event Bus 会扩大 Tiny Kernel 的
责任并模糊 Canonical authority，因此需要一个窄的、可选的 Outbox Capability。

## Decision

1. Outbox Intent 是 `shadow.profile.outbox-intent` typed Profile，复用 Canonical version rows、
   `CommitAuthority`、CAS 和现有 Owner/Space；不新增数据库表或 Proposal 审批表。
2. 只有通过 Core 最终 policy 检查的 reliable side effect 或预配置 emergency capability
   才能创建 Intent；未 allowlist 的 capability、未知 target、Secret 原文和任意脚本均拒绝。
3. Provider 调用前先提交 `pending`/`leased` Intent，调用后 Adapter 只返回 Result；Service
   再以 CAS 提交 `delivered`、`failed` 或 `unknown`。
4. `unknown` 不是成功，也不能盲目重试；reconciliation 必须提供 Provider 查询或明确人工
   evidence，未确认时继续保持 unknown。lease 重取复用同一 Intent 和 dedup key。
5. Outbox dedup scope 为 `outbox:{owner_ref}:{space_id}:{idempotency_key}`；同 digest
   重放复用稳定引用，不产生新 Intent/Result/Reconciliation，异 digest 返回结构化冲突。
6. 恢复导入只接受最小元数据、digest、状态和 lease 信息，不导入 Provider 私有状态、Secret
   或不可重建索引。

## Consequences

- Store outage 可以安全暂停现实副作用，并在恢复后继续同一 Intent；
- provider 重复调用风险由 capability 的 provider-side idempotency 和同一 Intent 引用控制，
  Core 不假设网络 exactly-once；
- 不提供通用排队/调度能力，长时 OperationJob、Router、Pulse 和跨组件 Erasure 仍需独立 ADR；
- `unknown` 可能长期可见，产品必须明确显示未确认而不是成功。

## Revisit conditions

真实可靠副作用需要批量吞吐、跨 Store delivery、provider-side dedup 或多租户配额时，
另建 capability-specific ADR；不得通过本 ADR 偷渡通用 Event Bus。
