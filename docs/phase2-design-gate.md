# Phase 2 设计闸门：Memory 与 Capability Profiles

状态：**Accepted / Phase 2 首个切片获准实现**

本文件已经获维护者接受，授权当前首个 Memory 生命周期切片进入实现。它不授权
Physical erase、Recall、Maintenance、SkillAsset、Integration 或 Portable Import/restore
业务实现；这些能力继续只维护 Contract 和设计。

本轮首个切片限定为 **Memory 生命周期**。SkillAsset、Integration、Recall、Maintenance
和 Portable Import/restore 继续只维护 Contract，不进入本切片。

## 已冻结的设计方向

- Canonical Memory 继续使用通用 Envelope 的版本语义，不建立平行的
  `MemoryVersion` 当前指针。
- Correction 在同一个 Memory ID 上创建新版本，并要求目标版本的
  `expected_version`；跨 Memory merge 创建新 Memory，并显式 supersede 输入 Memory。
- Logical delete 是普通 Canonical 新版本；physical erase 是独立 Erasure 操作，并保留
  不含敏感内容的 Tombstone，防止被旧导出或旧索引复活。
- Memory Maintenance / Recall 是可替换 Adapter；Adapter 只能提交 typed Proposal，
  不能直接写 Canonical Repository。
- SkillAsset 保留标准 Agent Skills bundle 原样；Shadow 治理信息放在 sidecar，绑定
  immutable snapshot / pinned revision 和确定性 digest，不修改 `SKILL.md` 或 bundle。
- Integration 与外部资产默认按需读取；派生索引可删除并从 Canonical 记录重建。

以上方向与 [ADR-0005](adr/0005-phase2-memory-lifecycle.md) 一致，已获维护者接受。
当前实现只覆盖下方首个 Memory 生命周期切片，不扩展到其他 Phase 2 能力。

## 首个切片的操作契约

| 操作 | Canonical 行为 | 版本条件 | 对外边界 |
| --- | --- | --- | --- |
| Create | 现有 Candidate → Commit，创建 Memory version 1 | 无 target version | `POST /v1/memories` |
| Correction | 同一 `record_id` 创建新 version，payload 设置 `supersedes_version` | 目标必须是当前 active head，必须匹配 `expected_version` | `POST /v1/memories/{memory_id}/corrections`，成功 `200` |
| Merge | 一个 Commit Batch 创建新 Memory，并将所有输入 head 提交为 `memory_state=superseded` | 每个 target 独立携带 `record_ref + expected_version`；任一冲突则整批失败 | Application/Contract only；本切片不新增 HTTP 路由 |
| Logical delete | 同一 `record_id` 创建新 version，Envelope `record_state=logically_deleted`；不改变 Profile `memory_state` 语义 | 目标必须是当前 active head，必须匹配 `expected_version` | `DELETE /v1/memories/{memory_id}`，成功 `202` |
| Physical erase | 未来独立 Erasure 操作，最终只保留 Tombstone | 不在本切片执行 | Contract/design only |

所有 correction、merge、logical delete 写操作都要求 `Idempotency-Key`、
`Expected-Version`（merge 为每个 target）、`X-Principal-Ref` 和 `X-Space-Id`。
用户命令经验证后直接进入 Commit，不新增 Proposal 表或持久审批流。

## 版本、权限与 anti-resurrection 规则

- Memory 稳定 ID 不因 correction 改变；旧版本保持不可变，当前 head 由 Repository 读取。
- Correction、merge target 和 logical delete 只能作用于当前 head；历史版本引用、已逻辑删除
  head 和 `memory_state=superseded` head 都返回结构化 `shadow.memory.head-not-active`。
- 所有写入 target 的 `owner_ref` 与 `space_id` 必须匹配请求的 principal / space；不匹配返回
  `shadow.memory.owner-space-mismatch`。完整读 ACL 延后 Phase 5。
- Merge 的所有 target 必须属于同一个 owner / space；新 Memory 继承该边界。
- 相同 scope + idempotency key + request digest 只返回原结果；digest 不同沿用
  `shadow.repository.idempotency-mismatch`。
- Store unavailable 时不创建 Candidate 以外的 Canonical 记录，不返回持久成功。

## 结构化错误目录

| Code | Category | 触发条件 |
| --- | --- | --- |
| `shadow.memory.not-found` | validation | target Memory 不存在 |
| `shadow.memory.owner-space-mismatch` | unauthorized | principal / space 与 target 不匹配 |
| `shadow.memory.head-not-active` | conflict | target 不是当前 active head |
| `shadow.memory.operation-invalid` | validation | payload、target 数量或关系不符合 Profile |
| `shadow.repository.expected-version-conflict` | conflict | CAS expected version 不匹配 |
| `shadow.repository.idempotency-mismatch` | validation | 同 key 搭配不同 request digest |
| `shadow.repository.unavailable` | unavailable | Store 不可用 |

## Physical erase / Tombstone 设计边界

本切片只冻结未来 Erasure 的安全顺序：先阻止新 Recall / derived projection，再由
各 Adapter 清除 Index、Cache、Graph、Backup copy 和敏感 payload，最后提交 `record_state=erased`
及 `TombstonePayload`。Tombstone 只能包含 `erased=true`、`erasure_ref` 和非敏感关系引用；
Adapter 不可达时不得报告完成。本切片不新增 Erasure API、Adapter、Job 或数据库表。

## 后续切片必须在实现前明确的边界

1. **Physical erase 与扩展 Memory 生命周期**：Tombstone、Erasure Adapter、source-dependent
   invalidation、状态转换、并发冲突和 anti-resurrection 的完整边界。
2. **Adapter Contract**：Maintenance / Recall 的输入输出、source dependency、
   unavailable / stale 语义，以及 Proposal 审批和 Commit 的责任边界。
3. **Skill / Integration**：bundle digest、sidecar 版本、外部引用失效、按需读取和
   `allowed-tools` 不得绕过 CapabilityEnvelope 的验证方式。
4. **Portable Import / restore**：manifest 与 record digest 校验顺序、owner / space
   边界、身份映射、版本冲突、幂等键、tombstone 处理和失败后的原子性。
5. **Derived index rebuild**：索引删除、重建输入快照、重建期间的可见性和恢复证据。

## 首个 Memory 生命周期切片退出条件

- correction、merge、logical delete 的 Service/Commit/API 契约和 fixture 已接受；
- correction 保留稳定 ID，merge 是 all-or-nothing，delete 后旧 Candidate / Index 不能恢复 active head；
- 每个 target 的 owner / space / expected version 都经过校验；
- replay、conflict、not-found、unauthorized、deleted-head、Store unavailable 和 restart 都有测试；
- OpenAPI 只实现现有 correction/delete 路由，不新增 merge 路由；
- 无新数据库表，无 Proposal 持久化，无 Physical erase 执行。

## Phase 2 总退出条件

- Memory Intelligence / Recall 替换不会丢失 Canonical Memory。
- correction、supersede、logical delete、physical erase 均有版本和恢复测试。
- 旧数据、旧导出和旧索引无法复活已删除或已擦除记录。
- Skill bundle 可被标准 Agent Skills 客户端读取，Shadow sidecar 不污染原 bundle。
- `allowed-tools` 不能授予实际 Capability；外部资产仍按需读取。
- Import / restore 只在完整性、身份边界、冲突和幂等规则被接受后实现。
- 派生索引删除后可从 Canonical records 确定性重建。

首个切片退出后，Phase 2 后续能力仍须分别完成设计闸门；在各自闸门接受前，继续只维护
文档，不提前实现业务代码。
