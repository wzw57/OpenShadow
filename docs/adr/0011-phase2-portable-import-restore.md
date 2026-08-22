# ADR-0011: Phase 2 Portable Import / restore snapshot 边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 0–1 已有经过 manifest/record digest 校验的 Export fixture，但没有受治理的写入边界。
Portable restore 必须防止篡改、跨 Owner/Space 写入、版本倒退和 Tombstone 复活，同时不把
Import 变成新的数据库或后台任务系统。

## Decision

1. Import 采用同步 snapshot restore：bundle 在进入 CAS 前完整校验；每个 stable record_id
   在一个 import snapshot 中最多一个 version，历史选择由调用方负责。
2. strict 模式要求 source Envelope owner/space 等于请求边界；remap_to_target 明确将全部
   owner/space/created_by 映射到目标 principal/space，保留 stable record ID，并重新计算
   result digest。
3. 新记录只能 version 1；已有记录只能 CAS 写入 current+1。相同 fingerprint 的当前版本
   skip，不同内容、gap、head conflict 或 erased anti-resurrection 整批失败。
4. erased 记录必须是无敏感 Tombstone；active/logically-deleted 内容不能覆盖 erased head。
5. 所有拟写 operation 通过现有 CommitAuthority/CommitPlan 原子提交；幂等 scope/key 与
   request digest 复用 Repository idempotency。
6. 结构化错误区分 invalid bundle、owner/space、identity、version、replay 和 unavailable；
   no_change 不伪造 commit。
7. 本 ADR 不引入 HTTP、DB、Proposal、Outbox、OperationJob、Backup、Secret/Provider 读取或
   Physical erase 执行。

## Rationale

快照级导入可用已有 CAS 保证全有或全无，并把完整性、身份边界和生命周期检查放在任何写入
之前。明确“一 record 一个 selected version”避免在不扩展 Store 事务语义的情况下部分恢复
历史，调用方仍可为每个版本分批执行受治理 import。

## Alternatives considered

- 直接把 Export 全部历史逐行写入 Store：现有 CommitPlan 禁止同批次重复 record，易产生半恢复，
  延后到专门 Migration capability。
- 自动 remap 任意 Owner/Space：可能越权，拒绝；只允许显式 remap_to_target。
- Import 先写再校验：篡改和 schema 错误会留下半成品，拒绝。
- 后台 OperationJob：本切片快照可同步完成，不扩展基础设施。

## Consequences

- Portable restore 可验证、可幂等、可原子回滚，且不泄漏 secret/erased payload。
- 完整历史迁移和大包异步处理仍需要 Migration/OperationJob 设计。
- no_change 没有 Canonical receipt；调用方应使用 result digest 和外部 import_id 审计。

## Revisit triggers

- 用户需要完整历史或超大包恢复；
- Store 获得原子多版本 Migration capability；
- remap 需要细粒度 ACL、签名身份或加密 key；
- Tombstone/Erasure 语义改变。
