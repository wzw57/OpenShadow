# Phase 4 Durable Outbox 状态

状态：**设计闸门 Proposed，尚未实现**

已提交设计闸门、ADR-0016、Schema 与 valid/invalid/result/reconciliation fixtures；维护者
接受前禁止创建 `OutboxService`、Adapter 写入逻辑、迁移或公开 Outbox 路由。

已冻结的边界：只处理 allowlisted reliable side effect/emergency capability；Provider 调用
前持久化 Intent；Adapter 不拥有 Canonical authority；dedup、lease、restart、Store outage
和 unknown reconciliation 都必须在实现切片中提供证据。

明确不在本切片：通用 Queue/Event Bus、OperationJob、真实 Provider/Secret、Router/Policy、
Semantic Pulse、跨组件 Erasure 和 Backup 内容。
