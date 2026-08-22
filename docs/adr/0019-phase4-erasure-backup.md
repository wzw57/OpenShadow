# ADR-0019：Phase 4 跨组件 Erasure 与 Backup Metadata 边界

- Status: Proposed
- Scope: Phase 4 Erasure / Backup Metadata 设计闸门
- Date: 2026-08-22

## Context

Physical Erase 已能安全处理单个 Canonical record，但真实用户删除还涉及 Index、Cache、Graph、
Integration 和 Backup copy。跨组件清除需要可重试的意图和逐组件证据；同时 Backup 只能保证
可验证的元数据，不应把 Secret、Provider 私有状态或不可重建索引带入用户资产。

## Decision

1. Shadow authority 创建一个带 scope、target set、policy、retention 和 component status 的
   `ErasureRequest`；Adapter 只能更新自己声明的状态，不能扩大 scope 或直接 Commit。
2. Erasure 顺序冻结为 quiesce → component erase → evidence/status → Canonical tombstone/complete
   decision。任一组件 unknown/unreachable/failed 时整体保持未完成，可恢复后继续同一 request。
3. Backup 只冻结加密、digest、manifest、opaque key ref、retention 和 erase schedule metadata；
   内容、密钥、真实设备备份和恢复执行不在本切片。
4. Erasure 和 Backup metadata 使用显式 dedup/idempotency；重复命令复用稳定引用，不能复活已
   erased 记录，不能把未确认备份清除显示为完成。
5. 本 ADR 不引入通用 Job、Queue/Event Bus、跨 Store 事务或公开 HTTP API。

## Consequences

- 删除承诺可以展示逐组件 pending/unreachable，而不是过度承诺 exactly-once；
- Portable Export/Import 和 Integrity manifest 成为恢复、篡改检测和 Erasure 证据的共同边界；
- 真实设备备份和外部系统清除需要各自 Capability/Adapter，不能从 metadata 推断完成。

## Revisit conditions

出现真实跨设备恢复、法规 retention deadline 或大规模组件清除需求时，另建窄的 Adapter/Store
Capability，保留本 ADR 的未知/失败诚实语义。
