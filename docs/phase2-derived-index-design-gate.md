# Phase 2 第三切片设计闸门：Derived Memory Index Rebuild

状态：**Accepted / Phase 2 第三切片获准实现**

本文件已获维护者接受，只定义派生 Memory Index 的重建与可见性边界，建立在已合并的
[Recall / Maintenance 第二切片](phase2-recall-maintenance-status.md)之上。未获接受前，
不得实现 Index rebuild 业务代码。

## 目标与边界

- Index 是 Derived State，不是 Canonical Memory、current-head、ACL 或删除权威；
- rebuild 只读取 Canonical Repository 的明确 snapshot，不经由 Recall 结果反向建索引；
- 只提供 Application Port、确定性 test adapter 和 Contract tests；
- 不新增公开 HTTP、数据库表、Index authoritative table、Proposal 持久化、Outbox、
  Backup 清理或 Physical erase；
- source-dependent invalidation、SkillAsset、Integration、Portable Import/restore 和
  完整多用户 ACL 不在本切片。

## Rebuild Contract

### 输入

`MemoryIndexRebuildRequest` 必须包含：

- `principal_ref`、`space_id`：限定 Canonical snapshot 的最小隔离边界；
- `rebuild_request_id`：日志与重放关联，不产生 Canonical idempotency row；
- `index_revision`、`index_schema_ref`：明确派生算法和 schema；
- 可选 `expected_snapshot_digest`：调用方要求只在指定 snapshot 上构建；
- `consistency`：`canonical`，不能静默降级为未标记的旧 snapshot。

Service 必须从 Repository 读取 active Memory heads，并为每条 entry 记录：
`record_ref`、`payload_digest`、owner/space、index revision 和确定性派生字段。原始
敏感 `typed_content` 不进入 Index entry。

### 输出

`MemoryIndexRebuildResult` 必须包含：

- `result_state`：`complete`、`stale` 或 `unavailable`；
- `snapshot_digest`、`index_snapshot_ref`、`index_revision`、`entry_count`；
- `entry_digests` 和整体 `result_digest`；
- `published`：仅在完整 digest/CAS 校验后为 true；
- `failure_detail`：结构化、可重试信息，不得声称 Canonical 已改变。

每个 Index entry 的 `record_ref` 必须仍由 Canonical Repository 验证为 active head。任何
logical deleted、superseded、erased 或非 active `memory_state` 都必须被排除。

## Snapshot、重建和发布语义

1. Service 在构建开始时取得按 `(record_id, version)` 排序的 active-head snapshot，并计算
   Canonical snapshot digest。
2. Adapter 在私有 staging 中生成 entry，按稳定键排序，计算 entry digest 和整体 digest。
3. Publish 前 Service/Adapter 重新读取 snapshot boundary；head、payload digest 或
   lifecycle 任一改变则丢弃 staging，返回 `stale`/`conflict`，不替换已发布索引。
4. 只有完整 staging 通过 schema、owner/space、digest 和 expected snapshot 校验后，才
   一次性切换可见版本；构建中、取消和失败期间旧版本不得被当作 fresh。
5. 重建重放使用相同 request、snapshot 和 revision 返回相同 digest；不同 snapshot 必须
   重新构建，不得复用旧结果。
6. Index 缺失、损坏、不可用或与 Canonical digest 不匹配时，Recall 必须返回
   `stale`/`unavailable`，不能返回未标记的旧命中。

## 错误与安全边界

| Code | Category | 触发条件 |
| --- | --- | --- |
| `shadow.memory.index-invalid` | validation | request、entry、schema 或 digest 不合法 |
| `shadow.memory.index-unavailable` | unavailable | Repository 或 Index Adapter 不可用 |
| `shadow.memory.index-stale` | conflict | snapshot/head/payload 在 publish 前发生变化 |
| `shadow.memory.owner-space-mismatch` | unauthorized | request 与 Canonical snapshot 边界不一致 |
| `shadow.memory.index-replay-conflict` | conflict | 相同 request 关联了不同 snapshot/revision |

Index Adapter 不得调用 Canonical Repository 写接口、CommitAuthority 或 MemoryService；
Index rebuild 不创建 Proposal，不改变 Memory version，不绕过 logical-delete 和
anti-resurrection。Tombstone、Physical erase、Backup/Cache/Graph 清除仍由未来 Erasure
流程负责。

## 实现前验收矩阵

- valid/invalid rebuild request、entry/result、schema 和 digest fixtures；
- active-head、deleted/superseded/erased anti-resurrection 与 owner/space 隔离；
- deterministic ordering、重复重放、不同 snapshot replay conflict；
- staging 在 publish 前不可见，任意 entry/schema/digest 错误 all-or-nothing；
- 并发 correction/delete 导致 stale，不覆盖新 Canonical head；
- Store/Index unavailable 不声称成功，restart 后可从 Canonical 重建；
- Documentation Drift 测试确认本切片没有新增 HTTP、数据库表或提前实现的业务能力。

## 闸门结论

维护者已接受本文件和 [ADR-0007](adr/0007-phase2-derived-index-rebuild.md)，现在创建
`phase2/derived-index-rebuild` 实现分支。实现必须严格限制在本闸门范围内，并在提交前补齐
Contract fixtures、重建原子性、CAS 冲突、重放和 restart 证据。
