# Phase 4 Semantic Pulse 设计闸门

状态：**Accepted / Phase 4 Semantic Pulse 获准实现**

本闸门是 Phase 4 的第四个独立切片，已获准实现。Semantic Pulse 是可替换、可关闭的 Proposal producer，
只产生 Trigger、Observation 或 Proposal；它不是系统健康、TTL、Lease、Timeout、恢复或
正确性依赖，也不是通用后台 Job/Queue。

## Frozen boundary

- Pulse 输入来自已授权 Event、Schedule/Clock Observation 或明确的 source reference；每次
  运行携带 `principal_ref`、`space_id`、budget、cooldown/dedup key、deadline 和 evidence refs。
- Pulse 输出必须是 `shadow.pulse.proposal`，包含 `proposal_kind`、目标 input schema、typed
  proposal payload、证据、过期时间和幂等 key。它不能直接创建或更新 Task、Memory、State、
  Action、Run 或 Canonical Record。
- 所有 work-bearing Pulse Proposal 必须重新进入现有 Admission，再由对应 Service/CommitAuthority
  验证、批准和提交；Pulse 的 confidence、rank 或模型文本不是权限事实。
- Pulse 可以返回 `source-unavailable`、`budget-exhausted`、`cooldown`、`unknown` 或空结果；
  不得把未知或未执行显示为成功，不得绕过 Store outage。
- Pulse 默认 at-most-once producer semantics；相同 `pulse:{owner}:{space}:{dedup_key}`
  和相同 digest 重放复用稳定 Proposal，不产生重复工作。跨进程 exactly-once 不在本切片承诺。

## Contract and errors

`PulseTrigger` 描述触发来源，`PulseObservation` 描述来源状态和 evidence，`PulseProposal`
描述待 Admission 的 namespaced input。`proposal_kind` 允许 `run`、`task`、`memory`、`state`
和 `action`，但允许的 proposal schema、capability、data scope、budget、approval 和 expiry
仍由 Core/对应 Profile 最终检查。

结构化错误至少包括：`shadow.pulse.source-unavailable`、`shadow.pulse.budget-exhausted`、
`shadow.pulse.cooldown`、`shadow.pulse.expired`、`shadow.pulse.invalid-proposal`、
`shadow.pulse.unauthorized`、`shadow.repository.unavailable`。

## Design-only 禁止事项

- 不新增 Pulse 专用 HTTP 路由、数据库表、通用 worker、Queue/Event Bus 或 OperationJob；
- 不让 Pulse 直接提交 Task/Memory/State/Action，不把 Pulse 当作 Scheduler/Clock 真相源；
- 不实现真实模型、外部 Event Stream、自动高风险 Action 或 Secret 读取；Deterministic Pulse
  Adapter 仅用于 Contract、budget、dedup、Admission 和拒绝路径。

## 评审与实现闸门

实现必须限定在本文件、[ADR-0018](adr/0018-phase4-semantic-pulse.md)、Schema、fixtures、
documentation-sync 和静态契约测试授权的边界内；`phase4/semantic-pulse-implementation`
分支复用 Admission/Proposal boundary，
并通过全量 pytest、Ruff、Alembic upgrade/downgrade 和 `git diff --check`。
