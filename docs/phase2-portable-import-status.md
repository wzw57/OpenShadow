# Phase 2 第七切片状态：Portable Import / restore

状态：**已实现 / 已合并**

设计闸门：[phase2-portable-import-design-gate.md](phase2-portable-import-design-gate.md)；ADR：
[0011](adr/0011-phase2-portable-import-restore.md)。

## 已交付

- `PortableImportRequest` / `PortableImportResult` 与同步 snapshot `PortableImportService.restore`；
- format/version、manifest digest、record digest、Canonical Envelope、Tombstone 和 typed
  payload schema 先校验，再执行 Owner/Space、identity mapping 和 CAS；
- strict / explicit `remap_to_target`，稳定 record ID 不变；单个 snapshot 每 record 只接收一个
  selected version；
- 新记录 version 1、已有记录 current+1、identical skip、version gap/different-content
  conflict 和 all-or-nothing CommitPlan；
- Repository 现有 idempotency receipt lookup，replay 不产生新 version，replay digest 稳定；
- erased Tombstone 不含敏感原文，active/logically-deleted 内容不能复活 erased head；
- tamper、duplicate/multi-version、owner/remap、replay/no-change、CAS、restart、Store
  unavailable 和 all-or-nothing fixtures/tests。

## 验收证据

- `tests/test_phase2_portable_import.py`：10 项通过；
- 全量 Ruff、pytest、隔离 SQLite migration upgrade/downgrade 和 PR CI 通过；
- Documentation Drift 确认无新 HTTP、数据库表、Proposal、Outbox、OperationJob 或 Backup。

## 明确未实现

- 完整历史 Migration、Backup image、异步 OperationJob、跨设备同步和加密 key 管理；
- 公开 Import API、Provider/Secret 读取、自动 OAuth、Physical erase/Erasure Adapter；
- 自动历史选择、细粒度 ACL 和大包分片恢复。

下一步必须先通过 Physical erase/Tombstone 设计闸门；未获接受前继续只维护文档。
