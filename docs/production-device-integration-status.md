# Production Voice / Device / Integration 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| Generic InteractionRequest / AdapterResult Contract | 已实现：peripheral Schema、valid/invalid fixtures |
| Capability / consent / expiry / scope checks | 已实现：确定性 Adapter 在 Provider 调用前拒绝 |
| Secret boundary | 已实现：只接受 `env:`/`vault:`/`keychain:`/`opaque:` reference，拒绝 inline secret |
| Idempotent result / unknown outcome | 已实现：同 key replay；unknown 不重复调用 |
| Voice/Device/Integration Service writes | 明确不直接写 Store；需通过 Action/Outbox/Commit 边界 |
| Real microphone / hardware / OAuth / webhook | Contract-only，未连接 |

首片没有新增公开 HTTP 路由、数据库表或 Vendor SDK。真实 Provider 接入必须在
`adapters/<vendor>` 中实现同一 Port，并另行完成 capability、consent、reconciliation 和
部署凭据验收。
