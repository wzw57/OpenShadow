# ADR-0024：Phase 5 Identity、Endpoint 与 Space ACL

- Status: Accepted
- Scope: Phase 5 Core Slice
- Date: 2026-08-23

## Context

Phase 0–4 已把 `owner_ref`、`space_id` 和 `endpoint_ref` 作为 Canonical 与 Admission
边界，但服务端当前仍信任浏览器 headers。Phase 5 需要多主体共享 Space，同时保留单用户
部署的简单性和 Canonical ownership 语义。

## Decision

1. Endpoint、Space、Membership、Invitation 使用 typed Profile 和现有 version rows，不新增
   SQL 表或通用认证服务。
2. Space membership 是共享读权限的唯一权威；owner/editor/viewer 角色采用闭集，默认 deny。
3. Invitation 使用一次性 opaque token 的 digest、expiry、revocation 和 accepted 状态；
   明文 token 不落库、不进入日志。
4. Endpoint pairing/revoke 采用 CAS 和 idempotency；revoked endpoint 不能发起新的
   work-bearing Admission。
5. 现有 owner/space headers 只作为 local-dev compatibility path。部署开启 session
   verifier 后，服务端认证 context 覆盖客户端声明，不信任客户端主体字段。
6. Profile Services 保持现有写入边界；ACL service 只提供 context 与授权决策，不能直接
   Commit。Canonical change 仍由各自 Service + CommitAuthority 完成。
7. 真实 OAuth/OIDC、Voice、远程同步和设备冲突解决另立 Adapter ADR。

## Consequences

- 共享 Space 读取可以逐步接入，而不改变既有记录 owner；
- 单用户 personal Space 保持兼容；
- 不提供生产级密码/令牌发行，必须由部署层配置 session verifier；
- 远程 Store 与多设备同步仍然是 Contract-only，不能由本地 membership 推断完成。

## Revisit conditions

需要跨设备离线写入、外部身份提供商、法规级审计或高并发 membership mutation 时，另建
专门的 Identity/Sync Adapter，并保持本文的 owner/space、CAS、token 不落库不变量。
