# ADR-0014: Phase 3 Continuity 与 State Profile 完成边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

State Profile 已完成首个生命周期切片。Phase 3 仍需要 Durable Task 连续性、Checkpoint/Handoff、
确定性 Schedule/Clock、State condition Admission 以及 Migration/Integrity capability，才能
满足连续性与可恢复性退出条件。

## Decision

1. Durable Task 是 typed Profile，不进入 Kernel enum；Kernel 只提供稳定 identity、Owner/Space、
   version、refs、Admission 和 Commit。
2. Task、Checkpoint、Handoff 和 Completion Proposal 均使用现有 Canonical rows、CommitAuthority、
   CAS 和 idempotency；不引入 Proposal 审批表或平行 Task store。
3. Checkpoint 保存可审计引用和 digest，不保存 Runtime 私有 Session。缺少 native resume 时只允许
   semantic handoff/new Attempt，必须显式标记，不能伪装恢复。
4. Schedule、Clock 和 State Resolver 是可替换 Adapter；它们只能产生 Trigger/Observation/Proposal，
   State condition 通过 Admission 进入 Run。
5. Migration 与 Integrity 是窄 Store capability；Portable Export/Import 复用现有实现，新增
   deterministic contract verification，不实现通用 Job/Queue/Outbox。
6. 对外只增加 Task query、generic Task Proposal 和窄 Checkpoint/Completion routes；不实现
   Action、Pulse、Router 或完整多用户 ACL。

## Consequences

- Task 可在 Runtime 崩溃和进程重启后从 Canonical refs 恢复，且不会错误宣称原 Session 恢复。
- 任何 Task/Checkpoint/Completion 写入都有 CAS、replay 和 Store outage 证据。
- Schedule/Resolver 不拥有 Canonical authority；Phase 4 可复用 Trigger/Proposal boundary。
- Migration/Integrity 能验证 portability，而无需引入新的持久化基础设施。

## Revisit triggers

- 需要复杂 Task Graph、Workflow Engine、异步 OperationJob 或跨组件 Outbox；
- 真实 Runtime 支持 native resume/reconciliation；
- State condition 需要多来源融合、预测或领域本体；
- Migration 需要跨 Store 长事务或加密 Backup。
