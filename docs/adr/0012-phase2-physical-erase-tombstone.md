# ADR-0012: Phase 2 Physical erase 与 Tombstone 边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 2 已交付 Memory correction/delete、source invalidation、SkillAsset、Integration 和
Portable Import/restore，但物理清除仍只有 Contract。用户拥有最终删除权；实现必须让旧
Canonical payload、Derived projection 和导出无法复活记录，同时避免在参考实现中凭空构造
跨组件 Erasure 平台。

## Decision

1. 提供单 record `PhysicalEraseService` 和窄 `ErasureAdapter`：quiesce → adapter erase →
   Tombstone Commit → purge old Canonical rows → adapter finalize。
2. Tombstone 只使用 Kernel `TombstonePayload`，包含 erased、erasure_ref 和非敏感关系引用；
   旧 payload、secret、Provider/Backup 内容不保留。
3. Commit 必须匹配 principal/space/expected version、使用 operation erase 和现有
   CommitAuthority/CAS；同 key replay 不重复副作用。
4. Adapter 失败、Store unavailable 或 finalize/purge failure 都返回结构化 failure，不报告
   completed；Commit 成功后的 finalize failure 不回滚 Tombstone，允许同 key 重试清理。
5. 参考 SQLite Store 只保留 Tombstone version，物理删除同 record 的历史 rows；不新增表或
   HTTP/API/Job/Outbox。
6. 已 erased head 只能保持 Tombstone，任何旧 Candidate、Export、Index、Source 或 Import
   active 内容都必须被拒绝。

## Rationale

先隔离/清除可重建副本，再提交最小 Tombstone，并清除 Canonical 历史，能同时满足用户擦除
承诺和 anti-resurrection。Adapter 可替换，参考实现不会假装已经连接所有外部系统。

## Alternatives considered

- 仅标记 logical delete：旧 payload 仍可被 Store/export 读取，不满足最终删除。
- 直接删除整条 record：失去 anti-resurrection 权威，旧导出可重建，拒绝。
- 引入跨组件 Erasure Job/Outbox：超出本切片，延后。
- 让 Adapter 直接 Commit：绕过 Shadow Authority，拒绝。

## Consequences

- Tombstone head 可证明记录已擦除，旧敏感版本不可读，重放可审计；
- 外部 Provider/Backup 的真正清除需要后续 Adapter capability，当前 Deterministic Adapter
  只能证明调用顺序和失败语义；
- 物理清除不可逆，测试必须使用隔离 Store 并验证没有恢复入口。

## Revisit triggers

- 真实外部 Store/Backup 需要异步确认或跨 record 编排；
- Tombstone 需要签名、保留期或跨设备 anti-resurrection；
- 用户需要可恢复删除或法律保留策略。
