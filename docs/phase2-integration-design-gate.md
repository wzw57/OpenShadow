# Phase 2 第六切片设计闸门：Integration Profile

状态：**Accepted / Phase 2 第六切片获准实现**

本闸门冻结用户外部 Integration 的 Canonical Profile，建立在 Stage 4 Adapter/Capability
Contract 和已交付 SkillAsset sidecar 之上。它只授权 Integration 注册/刷新、稳定身份、
Secret Reference 与健康状态的治理；不授权 Provider 网络调用、secret 读取、OAuth 流程、
Runtime binding 或新的 HTTP/数据库能力。

维护者“继续推进直到 Phase 2 完成”的授权作为本闸门接受依据。超出下述范围必须先更新
本文件和 ADR-0010。

## 已决定内容

### Canonical Profile 与边界

- Canonical record type 为 `shadow.profile.integration`，typed payload 使用
  `IntegrationPayload` schema；`integration_id` 是用户资产稳定身份，record version 是
  配置/治理版本。
- Envelope 的 Owner/Space 是唯一归属边界；Provider account ID、Adapter descriptor、
  config、secret 和 health observation 都用明确 reference，不复制外部 secret 或原文。
- `secret_refs` 只允许 `StableRecordRef`，永远不把 token、密码、OAuth code、cookie 或
  private key 写入 Canonical payload、日志、fixture 或导出。
- Adapter descriptor digest 必须是确定性 `sha256:` digest；更换 Adapter 或版本必须
  通过 refresh 明确改变 `adapter_ref`/digest，不改变 Integration stable identity。

### 注册与刷新 Contract

`IntegrationService.register` 接受：

- `principal_ref`、`space_id`、`integration_id`、namespaced `provider_kind`、不含 secret
  的 `external_ref`；
- `config_ref`、`secret_refs`、`adapter_ref`、`adapter_descriptor_digest`；
- `status`（enabled/disabled/unavailable/needs_reauth）、`lifecycle`（active/retired）和
  可选 `health_observation_ref`；
- `operation=create|refresh`、refresh 的 `expected_version` 与 `idempotency_key`。

Service 只验证 schema、digest 格式、引用唯一性和 Owner/Space/CAS；它不替 Adapter 调用
Provider、不验证远端 account 是否存在，也不把 status 当成新探测结果。健康新鲜度由独立
HealthObservation/Adapter Contract 负责；本切片只保存 observation reference。

`create` 以稳定 `integration_id` 生成 record identity；`refresh` 在同一 record_id 上追加
新 version，必须匹配 expected version，Owner/Space 不可改变。`retired` 只表达 Canonical
lifecycle，不执行外部撤销或删除。

### Authority、原子性与重放

- 所有写入通过现有 `CommitAuthority` + `CommitPlan`；不新增 Proposal 表、审批流、Outbox、
  OperationJob、HTTP 路由或数据库表。
- 同一 scope/key/request digest replay 返回稳定 record/version/result digest，不产生新
  version；同 key 不同内容返回 `shadow.integration.replay-conflict`。
- expected-version 不匹配返回 `shadow.integration.version-conflict`；Owner/Space 不匹配
  返回 `shadow.integration.owner-space-mismatch`；schema/reference/digest 非法返回
  `shadow.integration.invalid`；Store unavailable 返回 `shadow.repository.unavailable`。
- Commit 批次只包含该 Integration 的一个 operation；失败不留下半成品，Provider 无副作用。

### 安全、恢复与数据边界

- `external_ref` 只能是可审计标识或 URI，不得包含 secret material；测试会检查 payload 和
  导出中没有 token/password 等字段。
- secret、config、adapter descriptor 和 health observation 的生命周期由各自 Profile/
  Adapter 管理；Integration 丢失时不能伪造 provider state，Derived binding 可重建。
- old version、旧导出和旧 Adapter reference 不会改写当前 head；删除、导入/恢复、OAuth
  re-auth 和 Physical erase 在后续闸门定义。

## 结构化结果与验收证据

实现必须提供 `IntegrationRegistrationResult`（committed/replayed）、稳定 record/version、
adapter digest 和 result digest。Contract fixtures/tests 至少覆盖：

- create/refresh、stable identity、owner/space、expected-version 和 idempotency replay；
- descriptor digest/reference/schema/duplicate secret-ref 拒绝；
- enabled/disabled/unavailable/needs_reauth 与 health observation reference 的持久化；
- secret material 不进入 payload、日志、导出或错误；
- Store unavailable、restart、旧版本不可变和并发 refresh conflict；
- 不调用 Provider、不读取 Secret、不新增 HTTP/表/Proposal/Outbox/Job 的 Documentation Drift。

## 明确不在本切片

- Provider API、OAuth/PKCE、webhook、网络 health probe、secret vault 和 token rotation；
- Runtime/Model/Runner Binding、CapabilityEnvelope 签发、MCP/Executable 执行；
- Integration logical delete/physical erase、Portable Import/restore、Backup 清理；
- 完整多用户读 ACL、跨设备同步和后台 OperationJob。

## 闸门结论

本闸门已接受，允许创建 `phase2/integration-implementation` 分支。实现合并后进入
Portable Import/restore 设计闸门；所有未列能力继续只维护文档。
