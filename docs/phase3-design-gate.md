# Phase 3 设计闸门：State Profile 生命周期

状态：**Accepted / Phase 3 首个 State 切片获准实现**

本闸门只授权 State Profile 的首个生命周期切片。Durable Task、Checkpoint、Handoff、
Schedule/Clock、Migration/Integrity、真实外部 Integration 联动和 State Resolver 不在本切片实现。

## 已冻结的边界

- State 是 `shadow.profile.state` typed Profile；Canonical Envelope 负责身份、Owner/Space、
  version、record state 和提交，不把 State 语义搬进 Kernel enum。
- State Record 使用稳定 `record_id`。`state_key`、typed value、value schema、Evidence、source、
  `observed_at`、`expires_at` 和 source status 位于 typed payload。
- Observation 是来源产生的证据；StateProposal 是待验证的更新输入。两者都不能直接写
  Canonical Repository，必须经过 StateService、CommitAuthority 和现有 CAS。
- `freshness` 按当前时间与来源可用性在读取/验证时计算：过期不得返回 `fresh`；无可用证据返回
  `unknown`；有历史值但来源不可用或已过期返回 `stale`。`null` 不代表 unknown。
- create 不带 target；update/correction 和 logical delete 必须携带唯一 target、
  `expected_version`、`Idempotency-Key`、principal/space。Replay 返回原结果且不创建新 version。
- Owner/Space 必须与 target 一致。完整读 ACL 延后 Phase 5；本切片只执行 personal owner/space
  隔离和结构化 unauthorized 错误。
- 已逻辑删除或 erased 的 State head 不可 correction、merge、恢复或被旧 Observation 复活。
  Tombstone 不包含敏感原文；physical erase 继续复用 Phase 2 Erasure 边界。
- 通用 `POST /v1/proposals` 只接收 namespaced StateProposal；accept 路径最终由 StateService
  验证并提交。不存在 State 专用写入路由。
- `GET /v1/states` 和 `GET /v1/states/{state_id}` 是本切片唯一新增 State HTTP 读取边界。
- State Source Adapter 只返回确定性 Observation/availability result；Adapter、Resolver 和
  Integration 不得直接 Commit。
- 不新增数据库表、Proposal 审批表、OperationJob 或临时 merge/refresh 路由。

## 输入、错误与原子性

| 输入 | 目标/版本 | 结果 |
| --- | --- | --- |
| StateProposal create | 无 target | 创建 State version 1 |
| StateProposal update | 一个 `record_ref + expected_version` | 同一 State ID 新版本 |
| StateProposal logical_delete | 一个 `record_ref + expected_version` | 新 Canonical version，Envelope `record_state=logically_deleted` |
| Observation | Adapter/source 产生，不直接 Commit | 由 StateService 转成 Proposal |

错误码固定为：`shadow.state.not-found`、`shadow.state.owner-space-mismatch`、
`shadow.state.head-not-active`、`shadow.state.operation-invalid`、
`shadow.state.source-unavailable`、`shadow.repository.expected-version-conflict`、
`shadow.repository.idempotency-mismatch` 和 `shadow.repository.unavailable`。

一个请求的所有操作通过一个 CommitPlan 原子提交；任何 target conflict、身份错误或 Store
故障都不产生部分 State version。相同 idempotency scope/key 与相同 digest 返回原 receipt；
相同 key 搭配不同 digest 返回 validation error。

## API Contract

- `POST /v1/proposals`：`202`，返回 Proposal record reference；只允许
  `input_type=shadow.state-proposal`。
- `POST /v1/proposals/{proposal_id}/accept`：`200`，返回 decision 和 resulting State refs；
  接受时再次执行 expected-version、Owner/Space、deleted-head 和 freshness 校验。
- `GET /v1/states`：按请求 owner/space 返回 active State heads，可按 `state_key` 过滤。
- `GET /v1/states/{state_id}`：返回当前 State head 及计算后的 freshness；不存在或不属于边界
  返回结构化 not-found/unauthorized。

## 设计验收与退出条件

- State/Observation/StateProposal JSON Schema、valid/invalid/source-unavailable fixtures 和
  OpenAPI contract 已纳入离线 Contract Registry。
- owner/space、expected-version、replay、deleted-head、source unavailable、Store unavailable
  和 restart 语义都有测试计划；不新增表和迁移。
- `tests/test_documentation_sync.py` 能同时证明本闸门、ADR、状态文档、Schema、API 和实现
  surface 一致；任何 drift 必须使 CI 失败。
- 本闸门接受后才允许建立 `phase3/state-profile-implementation` 分支并提交业务代码。
