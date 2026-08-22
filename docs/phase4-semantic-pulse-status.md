# Phase 4 Semantic Pulse 状态

状态：**设计闸门 Proposed，尚未实现**

当前只提交 Semantic Pulse 的设计、ADR-0018、Schema 和 fixtures。维护者接受前禁止创建
`SemanticPulseService`、真实 Pulse Adapter、持久化冷却表或公开路由。

已冻结：Pulse 只能产生 Trigger/Observation/Proposal；work-bearing Proposal 必须重新进入
Admission；budget、deadline、cooldown、evidence、owner/space、dedup 和 source-unavailable
必须可验证；Pulse 不能直接创建 Task、Memory、State、Action 或 Run。

明确不在本切片：通用 Scheduler/Worker/Queue、真实 Event Stream、模型联动、自动高风险 Action、
Secret、跨组件 Erasure 和 Backup。
