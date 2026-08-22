# Phase 2 第八切片状态：Physical erase / Tombstone

状态：**已实现 / 已合并**

设计闸门：[phase2-physical-erase-design-gate.md](phase2-physical-erase-design-gate.md)；ADR：
[0012](adr/0012-phase2-physical-erase-tombstone.md)。

## 已交付

- `PhysicalEraseRequest` / `PhysicalEraseResult`、`ErasureAdapter` 和
  `PhysicalEraseService.erase`；
- quiesce → adapter erase → Tombstone Commit/CAS → Canonical history purge → finalize
  的确定性顺序；
- Kernel `TombstonePayload` 仅保存 erased、erasure_ref 和 non-sensitive relation refs；
- SQLite Repository `erase_history` 物理删除同 record 的旧 version rows，只保留 Tombstone；
- idempotency receipt replay/replay-conflict、owner/space、not-found、already-erased、version
  conflict、Adapter/Store unavailable、finalize failure 和 retry；
- Deterministic Erasure Adapter、restart、旧 Candidate/Export/Index anti-resurrection 证据。

## 验收证据

- `tests/test_phase2_physical_erase.py`：8 项通过；
- 全量 Ruff、pytest、隔离 SQLite migration upgrade/downgrade 和 PR CI 通过；
- Documentation Drift 确认无公开 HTTP、数据库表、Proposal、Outbox、OperationJob、Backup
  或跨组件 Erasure orchestrator。

## 明确未实现

- 真实 Provider/Secret/Backup/Index/Graph Erasure Adapter、跨 record Job、Outbox 和后台队列；
- 可恢复删除、跨设备同步、完整 ACL、公开 Erasure API 和 UI；
- 任何从 Tombstone 恢复原文的操作。

Phase 2 当前冻结范围已完成；后续能力必须另立设计闸门，不得回写本切片边界。
