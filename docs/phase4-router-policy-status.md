# Phase 4 Router / Policy 状态

状态：**已实现 / 已合并**

设计、ADR、Schema 和 fixtures 已接受；`RoutingPolicyService`、确定性 Policy Engine 和
Router Adapter 已在 `phase4/router-policy-implementation` 实现并合并。没有新增策略存储、
迁移或公开路由。

实现证据覆盖：Policy Engine 只能提出 PolicyDecision；Router 只能提出 BindingProposal；Core 保留
最终 capability/data scope/budget/side-effect/approval/expiry/revocation 检查；`target_kind`
保持 namespaced open-world；unknown/unavailable 不得伪造允许；AdapterRegistry 最终校验
target 和 capability，Router 不直写 Repository。207 项全量测试和迁移闸门已通过。

明确不在本切片：复杂 Policy Language、Routing Rule UI、评分缓存、真实 Provider、Secret
读取、Semantic Pulse、跨组件 Erasure 和 Backup。
