# Phase 4 Action & Proactivity 设计闸门

状态：**Accepted / Phase 4 首个 Action 生命周期切片获准实现**

## 总体边界

Phase 4 按独立切片推进。首个切片只冻结并实现 Action 生命周期；Durable Outbox、Router/Policy
Adapter、Semantic Pulse、跨组件 Erasure 和 Backup Metadata 继续保留为后续独立闸门。

Action 是 typed Profile，不进入 Tiny Kernel 永久 enum。Canonical record version rows、
`CommitAuthority`、`CommitPlan`、Owner/Space、Expected-Version 和现有 Proposal 边界继续复用，
不新增数据库表。

## Action Profile

- Record type：`shadow.profile.action`；Proposal 仍使用 `shadow.proposal`，通过
  `proposal_type=shadow.action-proposal` 或 `shadow.action-approval-proposal` 区分。
- Action payload 必须包含 `action_kind`、`target_ref`、结构化 `typed_parameters`、
  `data_classification`、`side_effect_level`、`required_capabilities`、`deadline`、
  `secret_refs`、`lifecycle` 和 `idempotency_key`。
- `secret_refs` 只允许不透明引用；禁止 Secret 原文、脚本、shell、任意代码或未声明参数。
- 首片允许 `none`、`low`、`medium` side effect；high-risk、未知 Capability、restricted
  data 或不满足 deadline 的请求确定性拒绝。
- Lifecycle 为：`pending`、`approval_required`、`approved`、`executing`、`succeeded`、
  `failed`、`unknown`。首片不实现 cancelling/cancelled。

## Proposal、Approval 与 Commit

1. Action Proposal 通过现有 `POST /v1/proposals` 提交并持久化 pending Proposal。
2. `POST /v1/proposals/{proposal_id}/accept` 校验 Profile、Owner/Space、Capability、
   policy 和 deadline；Proposal 与 Action 在同一 CommitPlan 中原子创建。
3. `none/low` side effect 进入 `approved`；`medium` 进入 `approval_required`。
4. Approval 也是 namespaced Proposal，必须携带 `action_ref`、`expected_version`、
   `approver_ref`、decision 和 evidence refs；批准/拒绝与 Action 版本更新原子提交。
5. Provider 执行前先提交 `executing`；Provider 只返回 Result，不拥有 Canonical authority。
6. Result、unknown evidence 和 reconciliation 均通过 ActionService + CommitAuthority 写入。

## Provider 与 Unknown

确定性 Provider Adapter 只实现 contract/fixture 验证，返回 `succeeded`、`failed` 或 `unknown`，
并可提供 external reference。`unknown` 禁止盲目重试；reconciliation 必须携带 Provider 查询
结果或明确人工证据，未确认时继续保持 `unknown`。

## HTTP Contract

- 复用 `POST /v1/proposals` 接收 ActionProposal/ApprovalProposal；不新增 Action 创建路由。
- 扩展 Proposal accept dispatch 支持 Action 类型。
- 新增只读 `GET /v1/actions` 与 `GET /v1/actions/{action_id}`。
- 读取按 `X-Principal-Ref` 与 `X-Space-Id` 隔离。
- Proposal/accept/approval mutations 使用 `Idempotency-Key`；更新目标使用
  `Expected-Version`；所有 mutation 使用 Owner/Space headers。

## 错误、原子性与重放

结构化错误代码至少包括：`shadow.action.not-found`、`shadow.action.unauthorized`、
`shadow.action.invalid-transition`、`shadow.action.policy-denied`、
`shadow.action.capability-unsupported`、`shadow.action.secret-inline-forbidden`、
`shadow.action.unknown-outcome`、`shadow.repository.expected-version-conflict`、
`shadow.repository.idempotency-mismatch`、`shadow.repository.unavailable`。

所有跨 Proposal/Action 的变化使用一个 CommitPlan。Idempotency scope 为
`action:{owner_ref}:{space_id}`；相同请求重放返回稳定引用且不创建新记录，复用 key 搭配不同 digest
返回冲突。Provider 调用不在数据库事务中执行，必须先有可恢复的 `executing` 版本。

## 后续 Phase 4 闸门

- Durable Outbox：仅可靠跨边界副作用和 emergency capability，不建设通用 Queue/Event Bus；
- Policy/Router：外部组件只能提出 Policy Decision/BindingProposal，Core 做最终检查；
- Semantic Pulse：只能产生 Trigger/Observation/Proposal，并重新进入 Admission；
- 跨组件 Erasure/Backup：复用 Physical Erase、Portable Import/Export、Integrity boundary，
  不提前读取 Secret 或实现加密备份内容。

## 设计验收

本闸门只提交文档、ADR、Schema、fixtures、OpenAPI contract 和 documentation-sync 测试；
未创建 ActionService、Provider adapter、Action API runtime 或数据库迁移。设计接受后才创建
`phase4/action-implementation` 分支。
