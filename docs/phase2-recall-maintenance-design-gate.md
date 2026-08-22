# Phase 2 第二切片设计闸门：Memory Maintenance / Recall Adapter

状态：**Accepted / Phase 2 第二切片获准实现**

本文件已获维护者接受，授权 Memory Maintenance、Recall 和派生索引的最小 Adapter
边界进入实现。它不授权 source-driven invalidation、Physical erase、SkillAsset、
Integration、Portable Import/restore 或公开 Recall/Maintenance HTTP API。

## 目标与范围

第二切片建立在已合并的 Memory correction / merge / logical delete 基线上：

- Recall 是只读、可替换的查询 Adapter；它返回 Canonical Memory 的稳定
  `record_id + version` 引用和派生匹配信息，不拥有权威状态；
- Maintenance 是只读 Canonical snapshot 输入、typed Proposal 输出的 Adapter；它不能
  直接调用 Repository 或绕过 `CommitAuthority`；
- 派生索引可以删除并从 Canonical active heads 确定性重建；索引版本落后时必须显式报告
  stale，不能覆盖 Canonical 的删除、supersede 或新版本；
- 用户直接 correction / merge / logical delete 命令继续沿用现有 `MemoryService` 和
  `CommitAuthority`，不新增 Proposal 表或审批 UI。

本切片不实现 source connector 驱动的自动 invalidation、Physical erase、Erasure
Adapter、SkillAsset、Integration、Portable Import/restore 或公开 Recall/Maintenance
HTTP API。

## Recall Contract

### 输入

`MemoryRecallQuery` 必须包含：

- `principal_ref`、`space_id`：写入边界之外的最小读隔离；完整多用户 ACL 仍延后 Phase 5；
- `query_ref` 或规范化 query text 的 digest；原始 query 不写入 Canonical Memory；
- 可选 `memory_kinds`、`applicability_scope`、`limit` 和 opaque `cursor`；
- `consistency`: `canonical` 或 `bounded_stale`。默认 `canonical`，不得静默降级；
- `request_id`，用于日志和结果关联，不作为 Canonical 幂等写入。

### 输出

`MemoryRecallResult` 必须包含：

- `result_state`: `complete`、`stale` 或 `unavailable`；
- `items[]`：每项至少有 `record_ref {record_id, version}`、派生 `match_kind`、可选
  `score` 和 `index_snapshot_ref`；
- `result_digest`、`generated_at` 和 `next_cursor`；
- 不返回已逻辑删除、`memory_state=superseded` 或 `record_state=erased` 的 head；
- 每个 `record_ref.version` 必须仍由 Canonical Repository 验证，索引不得把历史版本
  冒充当前 head。

Recall Adapter 不能提交 Proposal，也不能因“命中”改变 Memory 生命周期。`canonical`
一致性无法满足时返回结构化 unavailable / stale，而不是返回未标记的近似结果。

## Maintenance Contract

### 输入

`MemoryMaintenanceRequest` 必须包含：

- `principal_ref`、`space_id`、`request_id`；
- 一组 Canonical `record_ref` 快照及其版本 / digest；
- `reason`（例如 duplicate、stale-source、quality-review）和可选 source refs；
- 明确的预算与上限，避免 Adapter 自行扫描整个 Store。

### 输出

`MemoryMaintenanceResult` 只能返回：

- `proposals[]`：符合现有 `MemoryProposalPayload` 的 correction、merge 或 invalidate
  提案，所有 target 独立携带 `memory_ref + expected_version`；
- 每个 proposal 的 `proposal_digest`、生成原因和 Adapter 版本；
- `result_state`: `complete`、`partial`、`unavailable`，以及可重试的 failure detail。

Adapter 输出先经过 Contract Registry 和 owner / space / active-head 校验，再复用现有
`MemoryService` 的 Commit 边界。Adapter 不得直接创建 Canonical version，不得把
`partial` 或 `unavailable` 声称为已提交。

## Derived index 边界

- 索引记录只保存稳定 `record_ref`、Canonical payload digest、索引 schema / revision 和
  可重建的派生字段；不成为第二个 current-head 指针；
- rebuild 输入是某个明确的 Canonical snapshot；只消费 active Memory heads；
- 删除或重建期间，Recall 返回 `stale` / `unavailable`，不能返回无状态标记的旧命中；
- rebuild 完成后使用确定性 digest 验证结果；索引缺失不会影响 Canonical correction、
  logical delete 或 anti-resurrection；
- 物理擦除仍由未来 Erasure 流程负责，本切片不清理 Backup、Cache、Graph 或 Index 的
  敏感副本。

## 错误与重放

| Code | Category | 触发条件 |
| --- | --- | --- |
| `shadow.memory.recall-invalid` | validation | query、scope、limit 或 cursor 不合法 |
| `shadow.memory.recall-unavailable` | unavailable | Recall Adapter 或所需索引不可用 |
| `shadow.memory.recall-stale` | conflict | 只能得到落后于 Canonical snapshot 的结果 |
| `shadow.memory.maintenance-invalid` | validation | snapshot、target 或 proposal 不符合 Profile |
| `shadow.memory.maintenance-unavailable` | unavailable | Maintenance Adapter 不可用 |
| `shadow.memory.owner-space-mismatch` | unauthorized | 请求边界与目标 Memory 不一致 |
| `shadow.repository.expected-version-conflict` | conflict | Proposal 提交时沿用现有 CAS 语义 |

Recall 是只读请求，不产生 Canonical idempotency row。Maintenance 的 `request_id` 只保证
同一 Adapter 调用可关联；真正提交时仍必须由调用方提供现有 Commit `Idempotency-Key`。
相同 proposal digest 可以重复验证，但不能自动重复提交。

## 对外边界与禁止事项

- 本切片只提供 Kernel/Application Adapter Port 和 Contract tests，不新增 HTTP 路由；
- 不新增数据库表、Index authoritative table、Proposal 持久化或审批流；
- 不把 Recall score、embedding、graph edge 或 Maintenance result 写入 Canonical Memory；
- 不允许 Adapter 持有 `CanonicalRepository` 写能力；
- 不改变已合并的 correction/delete OpenAPI 契约。

## 实现前验收矩阵

- Recall valid / invalid query、owner / space 隔离、active-head 过滤、deleted/superseded
  anti-resurrection、canonical / stale / unavailable 结果；
- Maintenance proposal schema、每个 target 的 expected-version、owner / space 和
  CommitAuthority 边界；
- 同一 snapshot 的确定性 result digest 和 index rebuild；
- Adapter 不可用时不生成 Canonical version；
- restart 后 Canonical Memory 仍是 Recall 的权威输入；
- Contract / OpenAPI 无新增 public route，现有 documentation-sync 检查保持通过。

维护者已接受本闸门和 ADR；实现必须继续遵守本文件的范围、同步测试和交付闸门。
