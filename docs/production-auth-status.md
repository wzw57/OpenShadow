# Production Auth / Session 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| AuthContext / 通用 AuthVerifier | 已实现：local-dev deterministic 与 OIDC-compatible JWT/JWKS Adapter boundary |
| Session token / revoke / restart-safe Canonical record | 已实现：只保存 digest、issuer、subject 摘要、生命周期和过期时间 |
| Idempotent exchange / logout | 已实现：同 key 重放复用 token/record；digest 不匹配返回结构化 conflict |
| Production header trust boundary | 已实现：`local-dev` 才兼容未验证 header；生产请求必须带已验证 session |
| Secret boundary | 已实现：`EnvironmentSecretResolver` 仅解析 `env:` 引用；Canonical 不保存 Secret 原文 |
| HttpOnly cookie / bearer session | 已实现：Cookie 为 HttpOnly，生产模式 Secure/SameSite=Lax |
| CSRF protection | Contract-only / 待补：当前 Cookie 写操作尚需独立 CSRF token 闸门 |
| 真实 OIDC issuer / provider wiring | Contract-only / 待部署配置验收 |
| 生产级多用户 Space ACL | Phase 5 Core 已有基础 membership；完整读 ACL 仍未完成 |

本切片验收证据：`tests/test_production_auth.py`、Auth Schema fixtures、OpenAPI auth paths、
`pytest -q`、Ruff 和 Alembic upgrade/downgrade。认证切片不引入厂商 SDK、数据库表或真实
OIDC issuer；部署时必须显式提供 `SHADOW_AUTH_MODE`、session secret 和 OIDC 配置。
