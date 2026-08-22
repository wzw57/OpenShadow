# Phase 4 Durable Outbox 设计闸门

状态：**Accepted / Phase 4 Durable Outbox 获准实现**

本闸门是 Phase 4 的第二个独立切片，已冻结 Durable Outbox 的最小语义和契约并获准实现。
Action 首片已经合并；Router/Policy、Semantic Pulse、跨组件 Erasure
和 Backup 必须继续使用各自独立的设计闸门。

## 目标与边界

Durable Outbox 是可选的 Store Capability，只服务已经通过 Core policy 的可靠跨边界副作用
和预配置 emergency capability。它不是通用 Queue、Event Bus、Workflow 或后台 Job 平台。
Outbox Intent 使用 `shadow.profile.outbox-intent` typed Profile，继续写入 Canonical record
version rows，并经过 `CommitAuthority`/`CommitPlan`；本切片不新增数据库表或 migration。

Provider 调用前必须先提交可恢复的 `pending`（或已取得 lease 的 `leased`）Intent。Outbox
Adapter 只能返回 Delivery Result，不能直接写 Canonical Repository。Store unavailable 时
不得调用 Provider，也不得声称副作用已经完成。

## Frozen contract

- Intent 必须引用已接受的 `action_ref`、target、allowlisted capability、参数摘要和
  `idempotency_key`；不复制 Action typed parameters，不包含 Secret 原文。
- `delivery_class` 仅允许 `reliable-side-effect` 或 `emergency`；能力 allowlist、目标类型、
  data classification、deadline 和 side-effect policy 在 Core 端最终检查。
- 生命周期冻结为 `pending`、`leased`、`delivered`、`failed`、`unknown`。首片不引入
  cancelling/cancelled 或自动高风险执行。
- Adapter 结果为 `delivered`、`failed` 或 `unknown`。`unknown` 必须保留 provider reference、
  原因和 evidence；禁止无证据盲目 retry，只能由 reconciliation 收敛或继续保持 unknown。
- lease 过期只允许重新取得同一 Intent 的 lease；不得创建第二个 Intent。dedup 依据
  `outbox:{owner_ref}:{space_id}:{idempotency_key}`，同 key 同 digest 重放返回稳定引用，
  同 key 不同 digest 返回 `shadow.repository.idempotency-mismatch`。
- 恢复导入只能恢复未终态 Intent 的最小元数据和 digest；不得导入 Provider 私有状态或 Secret。

## 操作输入和错误

Create/dispatch/reconcile 都需要 `X-Principal-Ref`、`X-Space-Id`、`Idempotency-Key`；更新
目标另外需要 `Expected-Version`。结构化错误至少包括：

| 条件 | 错误代码 |
| --- | --- |
| owner/space 不匹配 | `shadow.outbox.unauthorized` |
| action 或 target 不存在 | `shadow.outbox.not-found` |
| expected version 不匹配 | `shadow.repository.expected-version-conflict` |
| 同 key 不同 digest | `shadow.repository.idempotency-mismatch` |
| Store 不可用 | `shadow.repository.unavailable` |
| capability 未 allowlist | `shadow.outbox.capability-unsupported` |
| deadline/状态转换非法 | `shadow.outbox.invalid-transition` |
| Provider 未确认结果 | `shadow.outbox.unknown-outcome` |

所有 Intent、lease、Delivery Result 和 Reconciliation 的变化必须在一个 CommitPlan 中
原子提交。Provider 网络调用不在数据库事务内执行；调用前的 `leased` 版本和调用后的
Result 版本分别通过 CAS 写入。

## Design-only 禁止事项

- 不新增 Outbox 专用 HTTP 路由、数据库表、通用消息队列、后台 worker 平台或 OperationJob；
- 不读取 Secret、不保存 Secret 原文、不把 Outbox 当作 Action payload 的副本；
- 不允许 Adapter 绕过 CommitAuthority、不把 unknown 当作成功、不做无证据自动重试；
- 不实现真实 Provider 联动；deterministic adapter 仅用于 Contract/故障/重启测试。

## 评审与实现闸门

实现必须限定在本文件、[ADR-0016](adr/0016-phase4-durable-outbox.md)、JSON Schema、
fixtures、Contract/OpenAPI 变更和同步测试授权的边界内；`phase4/outbox-implementation` 分支
负责 Service、Adapter 和恢复路径，实现完成必须通过
全量 pytest、Ruff、Alembic upgrade/downgrade、`git diff --check` 和 documentation-sync。
