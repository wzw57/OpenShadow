# Phase 4 Durable Outbox 状态

状态：**已实现 / 已合并**

设计闸门、ADR-0016、Schema 与 valid/invalid/result/reconciliation fixtures 已接受；
`phase4/outbox-implementation` 已实现 `OutboxService`、确定性 Adapter 和 Commit/CAS
恢复路径，不新增迁移或公开 Outbox 路由。

已冻结的边界：只处理 allowlisted reliable side effect/emergency capability；Provider 调用
前持久化 Intent；Adapter 不拥有 Canonical authority；dedup、lease、restart、Store outage
和 unknown reconciliation 都必须在实现切片中提供证据。

验收覆盖 Intent 持久化先于 Provider、lease、dedup replay、delivery result、unknown 禁止
盲目 retry、evidence-backed reconciliation、Owner/Space、Capability、Store outage、
restart 和 Adapter 不直写 Repository。实现分支已通过全量合并闸门并合并到 `main`。

明确不在本切片：通用 Queue/Event Bus、OperationJob、真实 Provider/Secret、Router/Policy、
Semantic Pulse、跨组件 Erasure 和 Backup 内容。
