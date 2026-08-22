# ADR-0008: Phase 2 source-dependent Memory invalidation 边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 2 已完成 Memory lifecycle、Recall/Maintenance Adapter 和 Derived Index rebuild。
Memory Profile 已有 `source_refs`、`source_dependency` 与 `memory_state=invalidated`，但
Source Connector 的不可用/删除事件还不能安全地影响 Canonical Memory。下一切片必须避免
无界扫描、旁路写入、旧 Candidate 复活和把来源失效误当作 logical delete 或 Physical erase。

## Decision proposal

1. Source invalidation 只接受带 `source_event_ref`、`source_ref` 和显式
   `record_ref + expected_version` 的受限请求；本切片不根据 source_ref 自动扫描全库。
2. 每个 target 必须属于请求的 owner/space，且其当前 Canonical payload 的 `source_refs`
   包含请求 `source_ref`。未绑定来源的 Memory 返回结构化 `source-not-attached`，不写入。
3. `source_dependency` 决定动作：
   - `independent`：保留 active head，记录 `retained` 结果，不创建新版本；
   - `dependent`：同一稳定 ID 创建新 Canonical version，保持 `record_state=active`，只将
     payload `memory_state` 设置为 `invalidated`；不使用 `record_state=logically_deleted`；
   - `review_required`：不改变 Canonical，返回 `review_required`，等待用户或维护流程决定。
4. Dependent invalidation 的所有 target 通过现有 `CommitAuthority`/`CommitPlan` 一次提交。
   任一 expected-version、owner/space、source 绑定或 head 状态冲突时，整批不落盘。
5. 同一 `source_event_ref + target set + expected versions` 重放复用现有 Commit idempotency
   边界，不创建额外版本；同一事件改变 target 或 expected version 返回 replay conflict。
6. Invalidated head 不得被旧 Candidate、旧 Index、重复 source event 或“source restored”
   自动恢复。来源恢复只产生 observation/result；重新激活必须由未来明确的用户/治理命令
   经过独立 CAS 边界完成。
7. 本切片只提供 Application/Contract Service 和 deterministic fixtures；不新增公开 HTTP、
   Source Connector、数据库表、Outbox、Proposal 持久化、Physical erase 或跨组件清除。

## Consequences

- source-dependent Memory 会保留稳定 ID、版本关系和非敏感 provenance，但不再出现在 active
  list、canonical Recall 或新 Index snapshot 中；旧 Index digest 会失配并需重建。
- independent 与 review_required 不会被过度删除，调用方能看到明确的结果状态。
- Source Connector 仍不能直接写 Repository；所有 Canonical mutation 继续经过 CommitAuthority。
- Source event 的完整历史、connector lease、自动 fan-out 和多用户 ACL 仍须另行设计。

## Acceptance evidence required

- valid/invalid request、target、result 和 source dependency fixtures；
- independent/dependent/review_required 三种动作，record_state 与 memory_state 区分；
- 多 target all-or-nothing、每个 expected-version、owner/space、source-not-attached 和
  Store unavailable 测试；
- source-event 幂等重放、replay conflict、旧 Candidate/Index anti-resurrection 和 restart；
- no public HTTP、no new table、no Proposal persistence 的 Documentation Drift 检查。

本 ADR 已获维护者接受，允许创建 `phase2/source-dependent-invalidation` 实现分支；实现
仍必须严格遵守本 ADR 范围并补齐上述验收证据。
