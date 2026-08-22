# ADR-0007: Phase 2 派生 Memory Index 重建边界

- Status: Proposed
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

ADR-0006 已交付 Recall / Maintenance Adapter 的最小边界，但派生索引仍只是
Contract-only。下一切片需要定义如何从 Canonical Memory active heads 确定性地构建、
校验、发布和丢弃索引，避免把索引误当成第二个 current-head、ACL 或删除权威。

## Decision proposal

1. Index 是可删除、可重建的 Derived State，只保存稳定
   `record_ref`、Canonical `payload_digest`、index schema/revision 和派生字段；不保存
   敏感原文，不拥有 Memory lifecycle 或 owner/space 决策权。
2. Rebuild 必须绑定一个明确的 Canonical snapshot：只消费指定 owner/space 的 active
   Memory heads，并在构建开始时记录 snapshot digest。logical deleted、superseded、
   erased 和非 active `memory_state` 的记录不得进入索引。
3. 构建采用 stage-then-publish：先在 Adapter 私有 staging 中完成、排序和 digest 校验，
   再以单次可见性切换发布；失败、取消或 snapshot 变化不得暴露半成品。
4. Publish 前再次验证 Canonical snapshot。发现 head、payload digest 或 lifecycle 改变时，
   丢弃 staging 并返回结构化 `stale`/`conflict`，不得覆盖新版本。
5. Recall 只消费与当前 Canonical snapshot 匹配的 index；缺失、重建中或不匹配时返回
   `stale` 或 `unavailable`，不能静默返回旧命中。
6. 同一 `rebuild_request_id + snapshot_digest + index_revision` 重放必须产生相同结果，
   不创建新的 Canonical 记录；不同 snapshot digest 必须重新构建或显式冲突。
7. 本切片只提供 Application Port、确定性 Adapter 和 Contract tests；不新增公开 HTTP、
   数据库表、Proposal 持久化、Outbox、Backup 清理或 Physical erase。

## Consequences

- Canonical Repository 继续是唯一的 Memory truth，索引丢失不会丢失 Memory。
- Recall 可以区分 fresh、stale 和 unavailable，调用方不会把旧索引命中伪装成当前事实。
- Adapter 可以替换、删除或重建，但必须保留 snapshot/digest 证据。
- 真正的跨组件失效通知、持久 Index Store、后台 Job、Physical erase 和多用户 ACL 仍须
  另行设计，不由本切片隐式引入。

## Acceptance evidence required

- Index snapshot、entry、rebuild request/result 和错误 Contract fixtures；
- active-head 过滤、logical delete/supersede anti-resurrection、owner/space 隔离；
- deterministic ordering/digest、staging 不可见、publish 原子性和 snapshot CAS 冲突；
- 重放不新增 Canonical record，Index unavailable 不声称 Recall 成功；
- restart 后 Canonical 仍可重建 Index，损坏或缺失 Derived State 不影响 Canonical；
- 文档同步测试确认没有新增 HTTP 路由、数据库表或未授权 Phase 2 业务。

本 ADR 仍为 Proposed。维护者接受设计闸门后，才允许创建实现分支和代码 PR。
