# ADR-0027：Production Auth & Security Boundary

- 状态：**Accepted / 获准 Slice A 实现**
- 范围：AuthContext、AuthVerifier、Session、SecretResolver、local-dev bootstrap、审计
- 设计闸门：[production-auth-design-gate.md](../production-auth-design-gate.md)

## Context

现有 Phase 5 Core Slice 已完成 Endpoint、Space、Membership、Invitation 和读 ACL，但 API
仍保留单用户 local-dev headers。生产模式若继续信任这些 headers，会允许客户端伪造主体；若
直接引入某个 OAuth/OIDC SDK，又会把 issuer 和 token 私有语义写进 Core。

## Decisions

1. 以通用 `AuthVerifier` Port 将 credential 映射为 `VerifiedIdentity`，由服务端生成
   `AuthContext`；Core 不依赖具体 OIDC Vendor。
2. Session 使用 HttpOnly/Secure/SameSite cookie 或 Bearer；Canonical/SessionStore 只保存
   token digest、主体、issuer、expiry、revoke 状态和审计引用。
3. 生产请求只信任已验证 AuthContext；`X-Principal-Ref`/`X-Space-Id` 仅在显式
   `SHADOW_AUTH_MODE=local-dev` 下作为兼容 bootstrap。
4. Session revoke、授权拒绝和 Secret access 产生最小审计事件；token、claims、prompt、Secret
   和 Provider 私有 payload 不得进入持久层、日志、Export、错误体或 UI。
5. 首片实现 deterministic verifier、signed session 和 SecretResolver boundary；真实 OIDC
   issuer 通过独立 Adapter contract 联调，不提前写入 Core。

## Rejected alternatives

- 继续信任浏览器 Header：无法证明主体真实性和 revoke；
- 在 Kernel/Application 中直接导入 OIDC SDK：违反 Vendor isolation；
- 将 access/refresh token 原文写进 Canonical：扩大泄露和 Portable Export 风险；
- 用 local-dev fallback 隐式覆盖生产认证：会把测试便利变成权限绕过。

## Consequences

- local-dev 启动需要明确选择 auth mode；
- 生产部署必须提供 SessionStore、签名密钥和 SecretResolver；
- 真实 OIDC Provider 的 JWKS/PKCE/rotation 仍由后续 Adapter 实现和验证；
- 所有现有 API route 需要从 request context 获取主体，而不是直接读取任意 Header。
