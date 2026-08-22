# Phase 2 第二切片：Recall / Maintenance 状态

更新时间：2026-08-22

本文件记录已接受的 Recall / Maintenance Adapter 实现边界和验收证据。它不扩大
[ADR-0006](adr/0006-phase2-recall-maintenance.md) 的授权范围。

## 实现范围

| 能力 | 状态 | 主要证据 |
| --- | --- | --- |
| Recall query/result model | 已实现 | `MemoryRecallQuery`、`MemoryRecallResult` 与 valid/invalid fixtures |
| Canonical active-head guard | 已实现 | `MemoryRecallService` 过滤 logical deleted、superseded、erased head |
| Recall stale/unavailable semantics | 已实现 | `complete`、`stale`、`unavailable` result tests；`bounded_stale` 历史版本必须显式标记 |
| Maintenance snapshot boundary | 已实现 | `MemoryMaintenanceService` 校验 owner / space / active head |
| Maintenance typed Proposal validation | 已实现 | Profile Registry、target expected-version、budget 和 digest tests |
| Deterministic adapters | 已实现 | `DeterministicMemoryRecallAdapter`、`DeterministicMemoryMaintenanceAdapter` |
| Derived index contract | Contract-only | snapshot ref / digest / rebuild boundary；本切片不建立 authoritative index |

## 明确不在本切片

- 不新增 HTTP 路由、数据库表、Proposal 持久化或审批 UI；
- Recall / Maintenance Adapter 没有 Canonical Repository 写权限；
- 不实现 source-driven invalidation、Physical erase、Erasure Adapter、SkillAsset、
  Integration 或 Portable Import/restore；
- Recall score 和 Maintenance result 不改变 Canonical Memory 生命周期；实际提交仍需沿用
  `MemoryService`、CAS 和 `CommitAuthority`。

## 验收证据

- `tests/test_phase2_recall_maintenance.py`：active-head、owner / space、deleted-head、
  stale/unavailable、proposal validation、restart 和 no-commit 边界；
- `tests/test_documentation_sync.py`：已接受闸门、Service surface、OpenAPI 无新增路由；
- 全量 `pytest`、Ruff 和隔离 SQLite migration upgrade/downgrade。

后续 Physical erase、source-dependent invalidation、SkillAsset、Integration、Portable
Import/restore 和 Derived index rebuild 的完整实现仍须分别经过设计闸门。

下一切片设计闸门：[Derived Memory Index Rebuild](phase2-derived-index-design-gate.md)，
当前状态为 Proposed；在维护者接受前不得实现 Index rebuild 业务代码。
