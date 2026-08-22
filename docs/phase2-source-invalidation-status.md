# Phase 2 第四切片：Source-dependent Memory Invalidation 状态

更新时间：2026-08-22

本文件记录已接受 [ADR-0008](adr/0008-phase2-source-dependent-invalidation.md) 的实现证据，
不扩大第四切片设计闸门的授权范围。

## 实现范围

| 能力 | 状态 | 主要证据 |
| --- | --- | --- |
| Request/result Contract | 已实现 | `MemorySourceInvalidationRequest`、`MemorySourceInvalidationResult` 与 fixtures |
| Application Service | 已实现 | `MemorySourceInvalidationService` 统一校验并复用 CommitAuthority |
| independent / dependent / review_required | 已实现 | 三种 dependency action 与 no-change/review tests |
| Dependent invalidated version | 已实现 | 同一 stable ID 新 version，`record_state=active`、`memory_state=invalidated` |
| Owner/space/source binding | 已实现 | target head、owner/space 和 source_refs 校验 |
| All-or-nothing CAS | 已实现 | 多 target 预校验、CommitAuthority expected-version conflict tests |
| Source-event replay | 已实现 | 相同 idempotency replay 不新增 version；不同内容返回 replay conflict |
| Anti-resurrection / restart | 已实现 | list、Recall、Index、旧 Candidate 和 restart tests |

## 明确不在本切片

- 不新增 HTTP 路由、Source Connector、数据库表、Outbox 或 Proposal 持久化；
- 不自动扫描全库 source_ref，不自动激活 restored source；
- 不执行 Physical erase、Backup/Cache/Graph 清除、SkillAsset、Integration 或 Portable
  Import/restore；
- 所有 Canonical mutation 仍通过 `MemoryService` 的 CommitAuthority/CommitPlan。

## 验收证据

- `tests/test_phase2_source_invalidation.py`：dependency semantics、binding、CAS、replay、
  unavailable、anti-resurrection、restart 和 fixtures；
- `tests/test_documentation_sync.py`：Accepted gate、Service surface 和无新增 HTTP/DB；
- 全量 `pytest`、Ruff 和隔离 SQLite migration upgrade/downgrade。

后续 SkillAsset、Integration、Portable Import/restore 和 Physical erase 仍须分别经过设计闸门。
