# Documentation Synchronization Rules

本文件是开发过程中的 Documentation Drift 闸门。它不替代 ADR、OpenAPI 或 JSON
Schema；它规定这些工件在实现发生变化时如何保持同步。

## Source-of-truth matrix

| 事实 | 权威来源 | 必须同步的证据 |
| --- | --- | --- |
| Public route、method、status、headers | `contracts/openapi/openapi.yaml` | FastAPI route、API tests、对应状态文档 |
| Canonical version / lifecycle semantics | Accepted ADR、design gate、JSON Schema | Service implementation、contract fixtures、lifecycle tests |
| 当前交付状态 | `docs/phase*-status.md`、`docs/roadmap.md` | PR description、CI evidence；不得保留已合并分支作为当前状态 |
| Fixture coverage | JSON Schema 与 fixture map | `tests/test_declared_contract_fixtures.py`、对应 Contract test |
| 未授权范围 | Accepted design gate / ADR | 状态文档和 PR body；未获闸门不得实现 |

## Change protocol

涉及以下任一变化时，代码、契约、测试和状态文档必须在同一个 PR 中更新：

1. 新增或修改 public route、header、status code 或 error body；
2. 新增 Canonical operation、version relation、lifecycle state 或 persistence boundary；
3. 新增、删除或改变 Contract fixture；
4. Phase 状态、ADR 状态、实施分支或退出条件发生变化。

PR 描述必须列出：实现范围、明确未实现范围、对应文档路径和本地/CI 验收命令。合并后，
路线图只描述 `main` 的已交付状态，不把历史开发分支写成当前状态。

## Automated guard

`tests/test_documentation_sync.py` 会在 CI 中验证当前 Phase 2 生命周期实现的核心方法、
correction/delete 路由、四个必需写入 headers、OpenAPI 路径以及 merge 无公开 HTTP 路由。
如果实现或契约改变而没有同步状态文档，CI 必须失败，促使 PR 同步更新，而不是事后补文档。

后续 Phase 2 能力（Physical erase、Recall、Maintenance、SkillAsset、Integration、
Portable Import/restore、Derived index rebuild）必须先建立自己的设计闸门，再加入新的
source-of-truth 条目和同步测试。

Phase 3 State Profile 也必须先维护 `phase3-design-gate.md`、ADR-0013、状态文档、State
Schema、fixtures、OpenAPI 和 `StateService`/Adapter surface；同步测试必须在实现或契约
改变而文档未更新时失败。Durable Task、Checkpoint/Handoff 等后续切片不得借用本闸门提前实现。

Phase 3 完成切片必须同步 `phase3-completion-design-gate.md`、ADR-0014、continuity Schema、
Task/Checkpoint/Schedule/Integrity fixtures、OpenAPI、实现 surface 和
`phase3-completion-status.md`；任何一项漂移都必须使 CI 失败。

Phase 4 Action 首片必须同步 `phase4-design-gate.md`、ADR-0015、Action Schema、Action/Approval/
Provider/Reconciliation fixtures、OpenAPI、`ActionService`/deterministic Adapter surface 和
`phase4-action-status.md`。设计闸门接受前禁止实现 Action 业务代码；Outbox、Router、Pulse、
跨组件 Erasure 和 Backup 必须另建闸门。
