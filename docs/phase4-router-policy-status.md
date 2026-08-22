# Phase 4 Router / Policy 状态

状态：**设计闸门 Proposed，尚未实现**

当前只提交 Router/Policy 的设计、ADR、Schema 和 fixtures。维护者接受前禁止创建
`PolicyService`、`RouterService`、真实 Adapter、策略存储或公开路由。

已冻结：Policy Engine 只能提出 PolicyDecision；Router 只能提出 BindingProposal；Core 保留
最终 capability/data scope/budget/side-effect/approval/expiry/revocation 检查；`target_kind`
保持 namespaced open-world；unknown/unavailable 不得伪造允许。

明确不在本切片：复杂 Policy Language、Routing Rule UI、评分缓存、真实 Provider、Secret
读取、Semantic Pulse、跨组件 Erasure 和 Backup。
