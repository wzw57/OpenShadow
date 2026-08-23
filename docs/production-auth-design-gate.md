# Production Auth & Security 设计闸门

状态：**Accepted / 获准 Slice A 实现**  
分支：`production/auth-design-gate` → `production/auth-implementation`  
依赖：`production-readiness-design-gate.md`、ADR-0024、ADR-0026

本闸门只授权生产身份、Session、Secret reference、审计和请求上下文收口。它不授权
Voice、Remote Store、Runtime Tool bridge 或 OAuth Vendor SDK 进入 Core。

## 1. 目标与边界

当前 local-dev API 允许通过 `X-Principal-Ref`、`X-Space-Id` 兼容单用户测试。生产模式必须
由受信 Auth Adapter 验证 credential，再由服务端生成不可伪造的 `AuthContext`；客户端声明
只能作为 local-dev bootstrap 输入，不能覆盖已验证主体。

```text
Cookie / Authorization Bearer
             │
             ▼
AuthVerifier Port（Vendor-neutral）
             │ verified subject / issuer / audience / expiry
             ▼
SessionService + SessionStore
             │ opaque AuthContext
             ▼
FastAPI request context → IdentityService / Space ACL / Application Services
```

## 2. Frozen contract

### 2.1 AuthContext

最小非敏感 context：

- `principal_ref`：由 `issuer + subject` 稳定派生，不接受浏览器自由填写；
- `issuer`、`audience`、`auth_method`、`authenticated_at`、`expires_at`；
- `session_ref`、`endpoint_ref`；
- `claims_digest`：只用于审计关联，不保存完整 claims 或 token。

AuthContext 不包含 access token、refresh token、Cookie 原文、Secret 或 Provider 私有 payload。

### 2.2 AuthVerifier Port

```python
verify(credential: str) -> VerifiedIdentity
```

Core/Application 只依赖 Port。具体 OIDC issuer、JWKS、PKCE、token exchange 和 SDK 只能在
独立 Adapter 中实现。首个实现提供：

- `DeterministicAuthVerifier`：测试/本地 fixture 专用；
- `SignedSessionVerifier`：校验 Shadow 自己签发的 HttpOnly session；
- `OidcAuthVerifier`：Contract/Adapter boundary，生产 issuer 配置由部署提供，不硬编码厂商。

### 2.3 Session

- 浏览器使用 HttpOnly、Secure、SameSite=Lax cookie；跨站写操作必须通过 CSRF token；
- API 客户端可使用 Bearer session；
- session token 只在客户端和 verifier 中出现，Canonical 只保存 token digest、subject、issuer、
  issued/expiry、revoke 状态和审计引用；
- logout/revoke 必须幂等；过期、撤销、issuer/audience 不匹配均拒绝；
- SessionStore 必须在生产模式跨进程/重启可恢复；local-dev 可使用内存实现但必须显式开启。

### 2.4 SecretResolver

```python
resolve(secret_ref: str, *, purpose: str) -> SecretLease
```

SecretResolver 只能向 Adapter 提供短期 lease；不得被 Profile、Repository、日志、OpenAPI、
错误体或 Web UI 读取。开发模式允许环境变量引用，生产模式必须通过显式 SecretResolver
配置启动检查。

### 2.5 Request context precedence

1. 生产模式：验证后的 AuthContext 是唯一主体来源；
2. 如果 credential 缺失或无效，返回结构化 `shadow.auth.unauthenticated`；
3. local-dev bootstrap：仅在 `SHADOW_AUTH_MODE=local-dev` 时允许默认主体或兼容 headers；
4. 即使 local-dev headers 被接受，也必须经过现有 `IdentityService.require` 的 Space/Endpoint
   校验；
5. 不允许一个请求同时使用已验证 Session 和不同的主体 Header。

## 3. API contract

新增通用认证入口，不新增 Vendor 路由：

- `GET /v1/auth/session`：返回非敏感当前 session/context 摘要；
- `POST /v1/auth/session`：测试/受控 bootstrap 用 credential exchange，生产由 OIDC Adapter
  提供 callback/exchange；
- `POST /v1/auth/logout`：撤销当前 session，幂等；
- `GET /v1/auth/config`：返回 enabled auth methods 和 `local_dev` 状态，不返回 issuer secret。

所有写入口继续使用 `Idempotency-Key`；logout 使用 auth-scoped idempotency。错误统一为
`application/problem+json`：

- `shadow.auth.unauthenticated`（401）；
- `shadow.auth.invalid-credential`（401）；
- `shadow.auth.session-expired`（401）；
- `shadow.auth.session-revoked`（401）；
- `shadow.auth.context-mismatch`（403）；
- `shadow.auth.csrf-failed`（403）；
- `shadow.auth.store-unavailable`（503）。

## 4. 审计与隐私

审计事件保存 operation、principal/session digest、endpoint、space、result、correlation 和
时间；禁止保存 token、Cookie、Authorization header、完整 claims、prompt、Secret 或 Runtime
私有事件。审计写入失败时：

- 安全敏感的 revoke/permission change 不得声称成功；
- 只读 session introspection 可以返回 unavailable；
- 不能通过重试制造重复 revoke 或重复审计事实。

## 5. 测试与退出条件

- deterministic verifier valid/invalid/expired/audience/issuer fixtures；
- signed session tamper、replay、expiry、revoke、restart 和 idempotency；
- 生产模式拒绝 unverified `X-Principal-Ref`/`X-Space-Id`；
- local-dev 模式行为保持兼容且显式可见；
- AuthContext 与 IdentityService/Space ACL 的 owner/editor/viewer 隔离；
- CSRF、CORS、cookie flags、redaction、rate-limit contract；
- Store unavailable 不声称 login/logout/revoke 成功；
- OpenAPI、Schema、documentation-sync、Ruff、全量 pytest、Alembic 和 Web smoke 通过。

本闸门不授权真实 OIDC issuer 联网登录；真实 issuer 联调作为后续 Adapter 验收证据，不能
替代 deterministic/security contract tests。
