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
| Web UI 参考客户端范围 | `docs/web-ui-design-gate.md`、ADR-0022 | `apps/shadow-web`、`/ui` 静态托管、Web UI 状态文档和浏览器验收 |
| Runtime Reliability / durable dispatch | `docs/runtime-reliability-design-gate.md`、ADR-0023 | Run/Attempt Service、Hermes Adapter、OpenAPI/错误体、恢复测试和 runtime 状态文档 |
| Phase 5 identity / endpoint / Space ACL | `docs/phase5-design-gate.md`、ADR-0024 | Identity Schema、fixtures、FastAPI routes、ACL tests、Web context 和 `phase5-status.md` |
| Runtime Management / Hermes launcher / Codex Adapter | `docs/runtime-management-design-gate.md`、ADR-0025、`docs/runtime-management-status.md` | Runtime profile schema、Supervisor/API、Adapter tests、Management UI、启动脚本和 runtime 状态文档 |
| Production Readiness / Release boundary | `docs/production-readiness-design-gate.md`、ADR-0026 | Auth/Secret/Store/Runtime/Backup/Operations slices、状态文档、release/restore/security evidence |
| Production Auth / Session / Secret boundary | `docs/production-auth-design-gate.md`、ADR-0027 | AuthContext/Verifier、SessionStore、auth OpenAPI、redaction/CSRF tests、`production-auth-status.md` |
| Production Store / Backup / Portable Sync | `docs/production-store-backup-design-gate.md`、ADR-0028 | Repository profile/configuration、Portable Import/Export、Backup Metadata、restore/outage tests、`production-store-status.md` |

## Vendor isolation rule

除具体 `adapters/<vendor>` 实现、该模块测试和部署配置值外，任何源代码层不得耦合
Vendor/Runtime 名称或私有语义。Server 组合根只能解析通用
`SHADOW_RUNTIME_ADAPTER_FACTORY=<module>:<factory>`，不得导入或判断 Vendor。新增
Vendor 时必须通过 Vendor-neutral Adapter Contract；不得在 Kernel、Application、
Profile/Schema、OpenAPI、Reliability 或 Web UI 增加 Vendor 分支。Documentation Sync
检查必须包含公共源代码扫描证据，防止新的 Vendor 条件泄漏到公共层。

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

Phase 4 Durable Outbox 必须同步 `phase4-outbox-design-gate.md`、ADR-0016、Outbox Schema、
Intent/Delivery/Reconciliation fixtures 和 `phase4-outbox-status.md`。设计接受前禁止实现
Outbox Service、Adapter delivery、迁移或公开 Outbox 路由；Outbox 只允许可靠副作用和预配置
emergency capability，不得漂移成通用 Queue/Event Bus。

Phase 4 Router/Policy 必须同步 `phase4-router-policy-design-gate.md`、ADR-0017、Routing Schema、
PolicyDecision/BindingProposal fixtures 和 `phase4-router-policy-status.md`。设计接受前禁止实现
Policy/Router Service、策略存储、评分缓存或公开路由；外部组件只能提出 Decision/Proposal，
Core 必须保留最终授权检查。

Phase 4 Semantic Pulse 必须同步 `phase4-semantic-pulse-design-gate.md`、ADR-0018、Pulse Schema、
Trigger/Observation/Proposal fixtures 和 `phase4-semantic-pulse-status.md`。设计接受前禁止实现
Pulse Service、持久化 cooldown、通用 worker 或公开路由；Pulse 产生的 work-bearing Proposal
必须重新进入 Admission。

Phase 4 Erasure/Backup 必须同步 `phase4-erasure-backup-design-gate.md`、ADR-0019、Erasure Schema、
ErasureRequest/BackupMetadata fixtures 和 `phase4-erasure-backup-status.md`。设计接受前禁止实现
跨组件 Erasure、Backup Service、真实 Adapter、密钥/备份内容或公开路由；未确认组件不得报告
completed。

Phase 5 Core Slice 必须同步 `phase5-design-gate.md`、ADR-0024、Identity Schema、Endpoint/Space/
Membership/Invitation fixtures、OpenAPI、ACL service surface、Web context 和 `phase5-status.md`。
真实 OAuth/OIDC、Voice、远程 Store 与设备同步必须另建 Adapter 闸门，不能以本地 membership
实现替代。

Production Readiness 必须先同步 `production-readiness-design-gate.md`、ADR-0026 和对应 Slice
状态文档；认证、Secret、远程 Store、Runtime reliability、Voice/Device 和发布运维不得在
总体闸门接受前直接进入业务代码。每个 Slice PR 必须附 migration/restore、故障、安全和
documentation-drift 证据。

Production Auth Slice 必须同步 `production-auth-design-gate.md`、ADR-0027、AuthContext/Verifier
contract、Session/Secret fixtures、OpenAPI、FastAPI context wiring、redaction/CSRF/revoke/restart
测试和安全状态文档；真实 OIDC Vendor 只能在独立 Adapter 中出现。

Production Store/Backup Slice 必须先同步 `production-store-backup-design-gate.md`、ADR-0028、
Repository profile/configuration、Portable restore/backup fixtures、outage/restore tests 和
状态文档；未完成设计接受前禁止添加 PostgreSQL/云备份业务代码。
