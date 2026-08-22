# Phase 4 跨组件 Erasure / Backup Metadata 设计闸门

状态：**Proposed / 等待维护者接受**

本闸门是 Phase 4 的最后一个独立切片，复用 Phase 2 Physical Erase、Portable Export/Import
和 Integrity boundary。它只冻结跨组件 Erasure Intent、组件状态和加密设备 Backup Metadata
契约；不执行真实跨组件清除，也不保存加密备份内容。

## Erasure boundary

- `ErasureRequest` 由 Shadow authority 创建，包含 owner/space、明确 scope、target refs、
  idempotency key、policy/retention refs 和组件状态集合。组件集合必须可审计、可重复计算，
  不允许 Adapter 自行扩大 scope。
- 每个受管 Adapter 先 quiesce，再按 family capability 执行 erase，最后返回带 evidence 的
  component status。Store/Memory/Index/Cache/Integration/Backup 不能直接修改 ErasureRequest。
- 状态至少为 `pending`、`quiesced`、`erased`、`failed`、`unreachable`、`unknown`、`completed`。
  任一组件未确认时，整体不得声称 completed；恢复后继续同一 request，不创建第二个 request。
- Canonical Tombstone 不包含敏感原文、Secret、Provider 私有状态或不可重建索引；旧 Candidate、
  Index、Cache、Backup copy 和重复命令不能复活已擦除记录。外部原始来源只有在明确授权时才受影响。

## Backup metadata boundary

- 标准 Export/Backup metadata 只引用 Portable Export digest、format version、scope、完整性
  manifest、加密 key 的 opaque reference、retention 和 device/backup identity。
- Metadata 必须声明 `encrypted=true`，不得包含 Secret 原文、Provider 私有状态、Session、
  运行时凭据或可重建 Index/Cache/Graph 内容；加密设备备份内容、密钥托管和恢复执行延后。
- Backup 对 Erasure 的传播只记录 retention/erase schedule 和 evidence，不宣称已清除未确认的
  备份副本。恢复导入继续复用 Portable Import 的完整性、冲突和幂等边界。

## 错误、幂等和故障

结构化错误至少包括：`shadow.erasure.scope-invalid`、`shadow.erasure.component-unavailable`、
`shadow.erasure.partial-failure`、`shadow.erasure.already-completed`、
`shadow.backup.metadata-invalid`、`shadow.backup.encryption-required`、
`shadow.repository.unavailable` 和 `shadow.repository.idempotency-mismatch`。

同一 `erasure:{owner}:{space}:{request_id}` 或 `backup:{owner}:{space}:{backup_id}` + digest
重放必须返回稳定引用；不同 digest 冲突。quiesce、adapter erase、status update 和最终
Tombstone 传播必须有明确顺序和失败语义，不在一个不可恢复的跨 Store 事务中假装原子。

## Design-only 禁止事项

- 不新增通用 Erasure Job、Queue/Event Bus、跨组件事务协调器或公开 Erasure/Backup 路由；
- 不执行真实 Provider/Secret vault/Backup 删除，不生成加密设备备份内容，不保存 Secret 原文；
- 不把 Backup Metadata 当作恢复数据，不把 `unreachable`/`unknown` 显示为 completed。

## 评审与实现闸门

设计阶段只提交本文件、[ADR-0019](adr/0019-phase4-erasure-backup.md)、Schema、fixtures、
documentation-sync 和静态契约测试。维护者接受后才创建
`phase4/erasure-backup-implementation` 分支；实现必须复用现有 ErasureAdapter、Portable
Export/Import 和 Integrity capability，并通过全量 pytest、Ruff、Alembic upgrade/downgrade
和 `git diff --check`。
