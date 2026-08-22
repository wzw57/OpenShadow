# Phase 3 完成闸门：Continuity 与 State Profile

状态：**Accepted / Phase 3 全部剩余切片获准实现**

Phase 3 的 State Profile 首个切片已按 ADR-0013 合并。本闸门冻结剩余的 Durable Task、
Checkpoint/Handoff、Schedule/Clock、State Resolver 边界以及 Migration/Integrity 能力，
完成后才允许把 Phase 3 标记为 complete。Phase 4 Action、Pulse、Outbox、Router 和完整
多用户 ACL 不进入本闸门。

## Durable Task Contract

- Record type 为 `shadow.profile.durable-task`，稳定 `task_id` 不因 Run、Runtime 或 Adapter
  更换而改变。
- Payload 至少包含 goal、completion criteria、lifecycle、Run refs、Checkpoint refs、
  Artifact refs、Trigger refs、waiting condition 和 deadline。
- 生命周期冻结为 `proposed → active → waiting/paused → completion_pending → completed`，
  以及 `failed/cancelled` 终态；Run success 不自动完成 Task。
- Task Proposal、Completion Proposal 和 lifecycle update 必须经过 TaskService、
  CommitAuthority、Owner/Space、expected version 和 idempotency；不新增审批表。
- Runtime/Planner/Workflow 只能提交 Proposal 或 Result，不能直接写 Task。

## Checkpoint / Handoff

- Checkpoint 是 Canonical reference，不复制 Runtime 私有 Session；内容可为 digest、artifact
  refs、runtime target/version 和 resumability metadata。
- Handoff 只声明 `native_resume` 或 semantic handoff 能力是否真实存在。
- 没有 native resume 时，恢复只能创建同一 Task 下的新 Run/Attempt，并明确标记
  `resumed_from_checkpoint=true`；不得声称恢复原 Session。
- Checkpoint 写入与 Task ref 更新必须在同一个 CommitPlan 内原子完成；重复 idempotency
  不创建额外 Checkpoint 或 ref。

## Schedule / Clock / State Condition

- Schedule Adapter 只产生确定性 Trigger Observation；Clock 是可替换的读取 Port，不依赖 LLM。
- Trigger 经现有 AdmissionService 进入 Request/Run；Adapter 不直接创建 Run、Task 或 Action。
- State condition 只读取 accepted State 的当前 freshness/value；满足条件时重新进入 Admission，
  不直接 Commit Task 或 State。
- 测试实现仅提供 deterministic clock/schedule/resolver，不读取真实外部 Integration。

## Migration / Integrity

- Store capability 通过 `MigrationPort`、`IntegrityPort` 表达，不新增数据库表。
- Migration 必须声明 source/target schema、semantic migration ref、reversible 与 digest；
  不兼容迁移拒绝执行。
- Integrity 必须验证 manifest digest、Canonical record digest、Owner/Space 边界和
  round-trip；失败返回 structured error，不产生部分 Commit。
- Existing Portable Export/Import 是当前 OperationJob-lite 实现；本闸门只补齐 capability
  contract、deterministic fixture 和验证服务，不引入通用 Job/Queue/Outbox。

## API 与错误

- 扩展通用 `POST /v1/proposals` 支持 `shadow.durable-task-proposal`；仍由 accept 路径提交。
- 新增 `GET /v1/tasks`、`GET /v1/tasks/{task_id}`。
- 新增 `POST /v1/tasks/{task_id}/checkpoints` 和
  `POST /v1/tasks/{task_id}/completion`；写入要求 Idempotency-Key、Expected-Version、
  X-Principal-Ref、X-Space-Id。
- 结构化错误包括 `shadow.task.not-found`、`shadow.task.owner-space-mismatch`、
  `shadow.task.invalid-transition`、`shadow.task.completion-conflict`、
  `shadow.continuity.capability-unsupported`、`shadow.schedule.invalid-trigger`、
  `shadow.migration.incompatible`、`shadow.integrity.digest-mismatch` 和已有 repository
  conflict/unavailable 错误。

## Phase 3 退出条件

- Runtime 崩溃后 Task 能从 Canonical Task/Run/Checkpoint/Artifact refs 恢复；
- 没有 native resume 时不会伪装原 Session 恢复；
- Run success 不自动完成 Task；
- Checkpoint/Handoff、Task lifecycle 和 Completion Proposal 全部经过 Authority；
- restart 后 Task lifecycle、refs、State accepted head 和 expires_at 可恢复；
- expired State 不再 fresh，source unavailable 不伪造 fresh；
- State condition 通过 Admission 重新产生 Request/Run；
- Migration/Integrity fixture、Store outage、冲突、replay、篡改和 all-or-nothing 测试通过；
- 不新增数据库表、通用 Workflow、Outbox、真实 Provider/Integration 或 Phase 4 Action。
