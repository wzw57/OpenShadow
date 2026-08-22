# Phase 2 第七切片设计闸门：Portable Import / restore

状态：**Accepted / Phase 2 第七切片获准实现**

本闸门把已有 Store Adapter Export fixture 变成受治理的 Portable Import/restore Application
边界。它定义一次同步、原子、snapshot 级导入；不实现 Backup、跨设备同步、OperationJob、
公开 HTTP 或新的数据库表。

## 已决定内容

### 输入、完整性和 snapshot 边界

`PortableImportService.restore` 接受：

- `principal_ref`、`space_id`、`import_id`、`idempotency_key`；
- `identity_mode=strict|remap_to_target`；remap 模式将全部 source owner/space 映射到请求
  principal/space，stable `record_id` 不变；
- 已生成的 `shadow.canonical-export` bundle。

导入顺序固定为：先验证 format/version、manifest digest、每个 record digest、Canonical
Envelope 和 typed payload schema，再执行 owner/space 校验、identity mapping、冲突计算和
Commit。Bundle 在一个 snapshot 中每个 `record_id` 必须至多包含一个 version；包含历史的
Export 由调用方先选定要恢复的 snapshot，Service 不静默丢弃历史版本。

### 版本、冲突与原子性

- 新 record 只能导入 version 1；已有 record 只能导入 `current_version + 1`，并以
  `expected_version=current_version` 通过现有 CAS；version gap、head conflict 或不同
  内容冲突整批拒绝。
- 已有同 version 且 canonical fingerprint（排除重新生成的 created/committed timestamps）
  相同的记录为 `skipped_identical`；不同内容为 conflict。所有拟写 operation 组成一个
  CommitPlan，任一失败则不创建其他记录。
- `record_state=erased` 必须满足 Tombstone schema 且不含敏感原文；已有 erased head 只允许
  同一 Tombstone fingerprint，不允许 active/logically_deleted 内容复活它。
- strict 模式要求每条记录 owner/space 与请求一致；remap 只改 Envelope owner/space 和
  created_by，不改 stable record ID、schema、typed payload digest 或 source manifest digest。

### Authority、幂等和结构化错误

- 所有写入通过现有 `CommitAuthority` + `CommitPlan`；不新增 Import 表、Proposal、Outbox、
  OperationJob、HTTP 路由或数据库表。
- 相同 scope/key/request digest replay 返回原 commit、record refs 和 result digest，不写
  新 version；同 key 不同 bundle/mapping 返回 `shadow.portable-import.replay-conflict`。
- `shadow.portable-import.invalid-bundle`：format、manifest、record、Envelope、typed
  schema 或 snapshot 不合法；
- `shadow.portable-import.owner-space-mismatch`：strict 边界不匹配；
- `shadow.portable-import.identity-conflict`：remap 后身份/归属不能安全映射；
- `shadow.portable-import.version-conflict`：head、gap、different-content 或 anti-resurrection；
- `shadow.repository.unavailable`：Store 不可用且不声称成功。

结果 `PortableImportResult` 至少包含 source manifest digest、imported/skipped record refs、
commit id、replayed/result digest 和 failure detail；无写入的全 identical snapshot 返回
`no_change`，其 digest 仍可验证但不伪造 commit。

## Tombstone 与敏感数据

- Import 前验证 erased Envelope 的 `TombstonePayload`；Tombstone 只允许 `erased=true`、
  `erasure_ref` 和 non-sensitive relation refs。
- 不导入 secret material、Bundle 原文、Provider token 或 erased record 的旧 payload；
  digest 只证明输入完整性，不扩大读取权限。
- 旧导出、旧 index 和旧 source candidate 不得把 erased/logically-deleted record 变回 active。

## 验收证据

- valid/tampered/duplicate/multi-version/erased bundle fixtures；
- manifest/record digest 顺序、Envelope/schema、strict/remap owner/space；
- create、version+1 update、version gap、different-content conflict 和全批次 atomicity；
- identical skip、idempotent replay/replay-conflict、Store unavailable、restart；
- Tombstone anti-resurrection 与敏感字段拒绝；
- Documentation Drift 确认没有 HTTP、数据库表、Proposal、Outbox、Job 或 Backup 副作用。

## 明确不在本切片

- Backup/restore image、长时 OperationJob、跨设备同步和加密密钥管理；
- 公开 Import API、后台队列、Outbox、Provider/Secret 读取；
- 自动选择历史版本、跨用户 ACL、Physical erase 执行和 Erasure Adapter 编排。

## 闸门结论

本闸门已接受，允许创建 `phase2/portable-import-implementation` 分支。实现合并后进入
Physical erase/Tombstone 设计闸门；未列能力继续只维护文档。
