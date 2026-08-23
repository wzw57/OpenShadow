# Production Operations / Release 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| Correlation ID | 已实现：请求复用/生成 `X-Correlation-Id` 并回写响应 |
| Structured redacted request log | 已实现：只记录 route/method/status/duration/correlation |
| Health/readiness | 已实现：Store unavailable 时 `/readyz` 返回 503 |
| Low-cardinality metrics | 已实现：`/metrics` 输出请求、错误、延迟总和、Store readiness |
| Production config fail-fast | 已实现：未知 Store backend、OIDC 缺配置、缺 session secret 直接失败 |
| Reference deployment | 已实现：Dockerfile、Compose、Windows release-check 脚本 |
| Release candidate local gate | 已实现：pytest、Ruff、Alembic upgrade/downgrade、diff check |
| External telemetry/chaos/load/security platform | Contract-only，需部署环境补充 |

Telemetry 明确不记录 principal、Session token、Secret、prompt、音频或 Provider 私有内容。
生产发布仍必须在目标环境完成 PostgreSQL/OIDC/Runtime Provider 联调、备份恢复演练和安全
与压力测试。
