# Phase 2 首个切片：Memory 生命周期状态

更新时间：2026-08-22

设计闸门与 [ADR-0005](adr/0005-phase2-memory-lifecycle.md) 已接受。本文件记录获准
实现的首个切片，不扩大 Phase 2 的授权范围。

## 当前已实现

| 能力 | 状态 | 主要证据 |
| --- | --- | --- |
| Correction | 已实现 | `MemoryService.propose_correction` / `commit_correction`；稳定 `record_id`、新版本和 `supersedes_version` |
| Merge | 已实现（Service / Contract only） | `propose_merge` / `commit_merge`；单个 Commit Batch 原子创建新 Memory 并 supersede 所有 target；无新增 HTTP 路由 |
| Logical delete | 已实现 | `logical_delete`、`DELETE /v1/memories/{memory_id}`；Envelope 使用 `record_state=logically_deleted` |
| Anti-resurrection | 已实现 | active-head、CAS、旧 Candidate、重复命令和 list head 过滤测试 |
| Owner / Space 写边界 | 已实现 | correction、merge target、delete 的 owner / space 校验 |
| Replay / conflict / outage | 已实现 | replay 不新增版本；并发冲突整批不落盘；Store unavailable 不声称成功 |
| Restart recovery | 已实现 | correction 后版本与 logical delete head 重启恢复 |
| Contract fixtures | 已实现 | correction / invalidate valid-invalid fixtures，既有 merge fixtures |

## 实现边界

- 所有 Canonical 写入继续通过 `CommitAuthority` 和现有 `CommitPlan`；没有新增表或持久
  Proposal / approval 流。
- correction 和 logical delete 只使用现有 OpenAPI 路由；merge 保持 Application / Contract
  边界，不新增临时 HTTP API。
- `GET /v1/memories` 只返回每个稳定 ID 的 active head；logical deleted、superseded
  和 erased head 默认不可见。
- Tombstone、Physical erase、跨组件清除和 Erasure Adapter 仍是 Contract / design-only，
  本切片不执行不可逆清除。

## 验收命令

```powershell
ruff check packages/shadow-kernel/src packages/shadow-application/src adapters/test-deterministic/src adapters/store-sqlite/src apps/shadow-server migrations tests
pytest -q
$env:SHADOW_DATABASE_URL = "sqlite://"
alembic upgrade head
alembic downgrade base
```

## 后续闸门

Memory Maintenance / Recall、source-dependent invalidation、SkillAsset、Integration、
Portable Import/restore、Derived index rebuild 和 Physical erase 必须分别维护设计稿并经
维护者接受后，才能进入新的实现分支。
