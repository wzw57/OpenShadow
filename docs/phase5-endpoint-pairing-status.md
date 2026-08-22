# Phase 5 Endpoint Pairing 状态

状态：**设计闸门 Proposed，尚未实现**

当前只提交 Phase 5 总体/首片设计、ADR-0020、Endpoint Schema 和 fixtures。维护者接受前禁止
创建 `EndpointService`、Pairing Adapter、设备注册表、ACL、同步逻辑或公开路由。

已冻结：Endpoint stable ID、namespaced endpoint_kind、trust_state、revoke anti-resurrection、
opaque proof/public-key refs、Admission context、Owner/Space、CAS、idempotency 和 Store outage。

明确不在本切片：Space membership/role/invitation、Home Space shared state、Remote Store/sync、
Voice/STT/TTS/wake word、distributed audio 和完整 Phase 5 多用户读 ACL。
