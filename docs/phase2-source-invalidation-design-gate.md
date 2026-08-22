# Phase 2 第四切片设计闸门：Source-dependent Memory Invalidation

状态：**Proposed / 等待维护者接受**

本文件定义来源不可用/删除事件影响 Memory 的最小 Canonical 边界，建立在已合并的
[Derived Index Rebuild 第三切片](phase2-derived-index-status.md)之上。未获接受前，
不得实现 source invalidation 业务代码。

## 目标与边界

- 只处理明确 source event 对明确 Memory targets 的影响，不做全库 source_ref 扫描；
- 所有 mutation 仍经过 `MemoryService`、`CommitAuthority` 和现有 CAS 事务；
- `memory_state=invalidated` 是 Memory lifecycle，不与 `record_state=logically_deleted`
  或 Physical erase 混用；
- 本切片只提供 Application Port、Contract models、deterministic fixtures 和 tests；
- 不新增公开 HTTP、Source Connector、数据库表、Outbox、Proposal 持久化、Backup 清理、
  Physical erase、SkillAsset、Integration 或 Portable Import/restore。

## Source Invalidation Contract

### 输入

`MemorySourceInvalidationRequest` 必须包含：

- `principal_ref`、`space_id`：最小 owner/space 写边界；
- `source_ref`、`source_event_ref`：不可变来源身份与本次事件身份；
- `source_state`：`unavailable` 或 `deleted`；`restored` 不直接激活 Memory；
- `targets[]`：每项 `record_ref + expected_version`，不得重复；
- `idempotency_key`、`request_id`、`observed_at` 和原因；
- 可选证据 refs，但不携带敏感来源原文。

Service 必须重新读取每个 target 的 current head，验证 owner/space、当前版本、
`record_state=active`、`memory_state=active` 和 `source_ref ∈ source_refs`。请求不得把
logical deleted、erased、superseded 或已 invalidated head 当作可重复激活目标。

### 输出

`MemorySourceInvalidationResult` 必须包含：

- `result_state`：`committed`、`no_change`、`review_required`、`conflict` 或 `unavailable`；
- 每个 target 的 `action`：`invalidated`、`retained`、`review_required` 或 `conflict`；
- stable `record_ref`、previous/resulting version（如有）、source event ref、result digest；
- `replayed` 和结构化 failure detail；不声称未提交的 target 已失效。

## Dependency semantics

1. `independent`：不提交版本，action=`retained`；来源事件不能把独立 Memory 删除或失效。
2. `dependent`：创建同一 `record_id` 的新 version；复制现有合法 Memory payload，设置
   `memory_state=invalidated`，保留 `record_state=active`、owner/space、source refs 和
   supersedes relation。旧版本保持不可变。
3. `review_required`：不提交版本，action=`review_required`；需要未来显式用户/治理命令。
4. 同一批次中 dependent target 只要一个验证失败，所有 mutation 不提交；independent /
   review_required 的结果也必须明确列出，不得隐藏批次冲突。
5. `source_state=restored` 只允许返回 observation/result 或 `unsupported`，不得自动把
   invalidated head 改回 active；恢复路径另行设计。

## Idempotency、CAS 与 anti-resurrection

- Commit idempotency scope 绑定 `source_event_ref` 和 target set digest；相同请求重放返回
  原结果且不创建新 version；不同 targets、source_ref 或 expected versions 返回
  `shadow.memory.source-replay-conflict`。
- Commit 前再次检查所有 target head；并发 correction、merge、logical delete 或 invalidation
  造成任一 expected-version 不匹配时，整批返回 conflict，Canonical 不变。
- `memory_state=invalidated` 不出现在 Memory list、canonical Recall 或新 Index snapshot；
  旧 Candidate、旧 Index、重复 source event 和 source restored 事件不得使其重新 active。

## 错误与安全边界

| Code | Category | 触发条件 |
| --- | --- | --- |
| `shadow.memory.source-invalidation-invalid` | validation | request、source state、target 或 evidence 不合法 |
| `shadow.memory.source-not-attached` | validation | target 的 source_refs 不包含 source_ref |
| `shadow.memory.source-owner-space-mismatch` | unauthorized | request 与 target owner/space 不一致 |
| `shadow.memory.source-replay-conflict` | conflict | 同一 source event 复用不同 target/version |
| `shadow.memory.source-head-conflict` | conflict | target 不是 active head 或 expected version 失配 |
| `shadow.memory.source-invalidation-unavailable` | unavailable | Canonical Store/Commit Authority 不可用 |

Source invalidation 不创建 Proposal 表，不绕过 CommitAuthority，不执行 Physical erase，也不
自动删除外部来源原始数据。Index、Recall 和 Cache 的清理/重建只通过各自 Derived Adapter
边界完成。

## 实现前验收矩阵

- valid/invalid request、source state、target and result fixtures；
- independent 保留、dependent 新版本 invalidated、review_required 不写入；
- logical deleted/erased/invalidated head、source-not-attached、owner/space 和 CAS 冲突；
- 多 target all-or-nothing、幂等 replay/replay conflict、Store unavailable；
- 旧 Candidate、旧 Index、重复 event 和 restored event anti-resurrection；
- restart 后 invalidated version 与 relation 可恢复；
- Documentation Drift 确认无新增 HTTP、数据库表或未授权组件。

## 闸门结论

维护者接受本文件和 [ADR-0008](adr/0008-phase2-source-dependent-invalidation.md) 后，
才创建 `phase2/source-dependent-invalidation` 实现分支。接受前只允许修改设计、fixtures、
状态记录和同步测试。
