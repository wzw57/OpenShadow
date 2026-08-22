# ADR-0013: Phase 3 State Profile 生命周期

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 2 已完成 Memory 与能力资产的生命周期。下一阶段需要保存可恢复但允许过期的世界状态，
同时保持 State Profile、Source Adapter 和 Tiny Kernel 的边界，避免把领域本体或 Resolver 智能
写进 Kernel。

## Decision

1. State 使用独立 namespaced Profile `shadow.profile.state`，Canonical Envelope 只负责稳定
   identity、Owner/Space、version、record state 和 Commit。
2. State payload 固定包含 `state_key`、typed value、value schema、Evidence/source refs、
   `observed_at`、`expires_at` 和 source status；freshness 是读取时按 TTL/来源状态计算的稳定语义。
3. Observation 与 StateProposal 是输入族。Source Adapter/Resolver 只能产生它们，StateService
   验证后通过 CommitAuthority 写入 State。
4. Create、update 和 logical delete 使用同一 Canonical record ID 的版本/CAS；旧版本不可变，
   replay 不创建新 version，deleted/erased head 拒绝旧输入。
5. 对外只扩展通用 Proposal POST/accept 和 State GET/list；不新增 State 专用写路由或审批表。
6. 本切片提供 deterministic State Source Adapter fixture，不读取真实 Integration，也不实现
   Durable Task、Migration/Integrity 或 OperationJob。
7. 不新增数据库表；SQLite 继续使用现有 Canonical record/version rows 和 idempotency receipt。

## Consequences

- State 可在重启后从 Canonical rows 恢复，TTL 到期不会继续声称 fresh。
- Source unavailable 不会伪造新值；历史值可标记 stale/unknown，后续刷新仍走 Proposal/Commit。
- 通用 Proposal API 的扩展是稳定契约，State 不再需要临时专用写入口。
- Durable Task 连续性与真实 Source/Resolver 集成仍需独立设计闸门。

## Revisit triggers

- 需要多来源融合、冲突解决或领域本体时；
- TTL 需要后台 scheduler 产生 Canonical transition 时；
- State 与 Durable Task/Action 共享条件触发时；
- 外部 Integration 需要异步 health、secret 或 reconciliation 时。
