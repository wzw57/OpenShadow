# Phase 2 第三切片：Derived Memory Index Rebuild 状态

更新时间：2026-08-22

本文件记录已接受 [ADR-0007](adr/0007-phase2-derived-index-rebuild.md) 的实现证据，
不扩大第三切片设计闸门的授权范围。

## 实现范围

| 能力 | 状态 | 主要证据 |
| --- | --- | --- |
| Rebuild request/result Contract | 已实现 | `MemoryIndexRebuildRequest`、`MemoryIndexRebuildResult` 与 index fixtures |
| Canonical active-head snapshot | 已实现 | `MemoryIndexRebuildService` 过滤 logical deleted、superseded、erased head |
| Entry payload/digest guard | 已实现 | `MemoryIndexEntry` 禁止 Canonical/sensitive content；entry/artifact digest 校验 |
| Stage-then-publish boundary | 已实现 | `MemoryIndexAdapter.stage/publish/discard` 与 staging 不可见测试 |
| Snapshot CAS / stale | 已实现 | publish 前二次 snapshot digest 检查，变化时丢弃 staging 并返回 `stale` |
| Replay / replay conflict | 已实现 | deterministic adapter 按 request/snapshot/revision 重放；不同 snapshot 返回 conflict |
| Deterministic Index Adapter | 已实现 | `DeterministicMemoryIndexAdapter`，不写 Canonical Repository |
| Persistent Index Store / HTTP | Contract-only | 本切片不新增数据库表、Index authoritative table 或公开路由 |

## 明确不在本切片

- 不新增 HTTP 路由、数据库表、Proposal 持久化、Outbox 或 Backup 清理；
- Index 不拥有 current head、Memory lifecycle、owner/space ACL 或删除权威；
- 不实现 source-dependent invalidation、Physical erase、Erasure Adapter、SkillAsset、
  Integration 或 Portable Import/restore；
- 不把 Index entry、score 或派生字段写回 Canonical Memory。

## 验收证据

- `tests/test_phase2_derived_index.py`：active-head、anti-resurrection、owner/space、digest、
  stage/publish、CAS stale、replay、unavailable、restart 和 invalid fixture 边界；
- `tests/test_documentation_sync.py`：Accepted 闸门、Application surface 和无新增 HTTP/DB；
- 全量 `pytest`、Ruff 和隔离 SQLite migration upgrade/downgrade。

后续 source-dependent invalidation、SkillAsset、Integration、Portable Import/restore 和
Physical erase 已分别通过设计闸门并合并实现；各切片仍保持独立的生命周期边界。

下一切片设计闸门：[Source-dependent Memory Invalidation](phase2-source-invalidation-design-gate.md)，
第四切片状态：[Source Invalidation](phase2-source-invalidation-status.md) 已实现。
