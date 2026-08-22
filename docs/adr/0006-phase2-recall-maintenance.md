# ADR-0006: Phase 2 第二切片的 Recall / Maintenance Adapter 边界

- Status: Proposed
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 2 首个切片已经把 Memory 的稳定 ID、版本、merge、logical delete 和
anti-resurrection 交付到 `main`。下一步需要让可替换组件查询和维护 Memory，但不能把
Recall score、索引或智能整理结果提升为第二套权威状态，也不能让 Adapter 绕过
`CommitAuthority`。

## Decision

1. Recall 只读返回经过 Canonical version 验证的 `record_ref` 和派生匹配信息；
   `canonical`、`bounded_stale`、`unavailable` 必须显式区分。
2. Maintenance 只接收受限 Canonical snapshot 并输出已声明 Profile 的 typed Proposal；
   correction、merge、invalidate 的提交继续复用现有 MemoryService / CommitAuthority。
3. Derived index 是可删除、可重建的 projection，绑定 Canonical payload digest 和 snapshot；
   它不拥有 current head、lifecycle 或 ACL 决策权。
4. 本切片只提供 Adapter/Application Port 和 Contract tests，不新增 HTTP 路由、数据库表、
   Proposal 持久化、Physical erase 或 source-driven invalidation。

## Consequences

- Recall/maintenance 实现可以替换而不会丢失 Canonical Memory；
- stale / unavailable 语义可被调用方正确处理，不会把旧索引命中伪装成最新事实；
- Maintenance 的智能结果仍需经过现有 Profile、owner / space、CAS 和幂等边界；
- 首个实现不能直接提供完整全文检索、embedding、graph 或跨组件清除能力。

## Acceptance evidence required before implementation

- Recall query/result、Maintenance request/result 和 error fixtures；
- active-head、deleted/superseded、owner / space、stale / unavailable 测试；
- proposal expected-version 与 CommitAuthority 边界测试；
- derived index snapshot / digest / rebuild 完整性测试；
- restart 后 Canonical remains authoritative 测试；
- maintainer 明确接受本 ADR 和设计闸门后，才创建 implementation branch。
