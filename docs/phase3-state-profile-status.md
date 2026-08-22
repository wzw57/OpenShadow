# Phase 3 State Profile 状态

状态：**已实现 / 已合并**

## 已完成

- [Phase 3 设计闸门](phase3-design-gate.md) 已接受；边界见 [ADR-0013](adr/0013-phase3-state-profile-lifecycle.md)。
- 已冻结 `shadow.profile.state`、State/Observation/StateProposal schema、TTL/freshness、
  Owner/Space、CAS、幂等、source unavailable 和 anti-resurrection 语义。
- 已加入 State schema、fixtures、Contract test case 和 OpenAPI 的 State read / generic Proposal
  submit contract。
- `StateService`、确定性 State Source Adapter、Proposal submit/accept、State list/get、TTL
  freshness 和 restart/CAS/replay 测试已完成。

## 实现边界

`phase3/state-profile-implementation` 已交付 `StateService`、确定性 State Source Adapter、
Proposal accept/Commit、`GET /v1/states`、`GET /v1/states/{state_id}` 和通用
`POST /v1/proposals`。不新增数据库表或迁移。

## 本切片明确不实现

- 真实外部 Integration 联动、State Resolver 和 OperationJob；
- State 专用写入路由、Proposal 审批表和完整 Phase 5 读 ACL。

Durable Task、Run checkpoint、Semantic Handoff、Schedule/Clock、State condition
Admission、Migration Adapter 与 Integrity manifest 已在 Phase 3 完成闸门中实现并合并，
详见 [Phase 3 完成状态](phase3-completion-status.md)。

## 设计验收条件

- Schema fixtures、错误目录、API contract 和文档同步测试已通过；
- replay、CAS、TTL、source unavailable、deleted-head、restart、Store outage 和 Adapter 不直写
  Repository 的证据已加入测试；
- Phase 4 Action、Outbox、Router/Policy、Semantic Pulse 和跨组件 Erasure/Backup
  必须各自经过独立设计闸门；本状态文档不授权提前实现这些能力。
