# Phase 3 State Profile 状态

状态：**设计闸门 Accepted；实现尚未开始**

## 已完成

- [Phase 3 设计闸门](phase3-design-gate.md) 已接受；边界见 [ADR-0013](adr/0013-phase3-state-profile-lifecycle.md)。
- 已冻结 `shadow.profile.state`、State/Observation/StateProposal schema、TTL/freshness、
  Owner/Space、CAS、幂等、source unavailable 和 anti-resurrection 语义。
- 已加入 State schema、fixtures、Contract test case 和 OpenAPI 的 State read / generic Proposal
  submit contract。

## 实现边界

下一分支 `phase3/state-profile-implementation` 将交付 `StateService`、确定性 State Source
Adapter、Proposal accept/Commit、`GET /v1/states`、`GET /v1/states/{state_id}` 和通用
`POST /v1/proposals`。不新增数据库表或迁移。

## 尚未实现

- Durable Task、Run checkpoint、Semantic Handoff、Schedule/Clock；
- 真实 Integration 联动、State Resolver、Migration/Integrity Capability、OperationJob；
- State 专用写入路由、Proposal 审批表和完整 Phase 5 读 ACL。

## 设计验收条件

- Schema fixtures、错误目录、API contract 和文档同步测试通过；
- 实现完成后须补充 replay、CAS、TTL、source unavailable、deleted-head、restart、Store outage
  和 Adapter 不直写 Repository 的证据；
- Phase 3 首个切片合并前，不得把 Durable Task 或 Action 能力标记为已实现。
