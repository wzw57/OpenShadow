# ADR-0005: Phase 2 首个切片的 Memory 生命周期边界

- Status: Proposed
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Phase 0–1 已提供 Memory Candidate → Commit、Canonical Envelope、CAS 版本和
Store outage 基线。Phase 2 需要扩展 Memory correction、merge 和删除语义，但不能
把 Memory Intelligence、Recall、Backup、Erasure orchestrator 或多用户 ACL 提前
塞进 Kernel，也不能通过临时 API 绕过 Proposal / Commit 边界。

现有 Profile Contract 已冻结 Memory payload、target + expected version、
`memory_state` 和通用 Envelope `record_state`。本 ADR 只决定首个 Memory 生命周期
切片的实现顺序和边界，不改变 Stage 4 的既有 Schema major version。

## Decision

### 1. Correction

Correction 作用于当前 active Memory head，在同一个 `record_id` 上创建新的 Canonical
version。请求必须携带目标 `expected_version`，新 payload 设置 `supersedes_version`；
旧版本永远不可变。已逻辑删除、superseded 或非当前 head 不可直接 correction。

### 2. Merge

Merge 使用一个 Commit Batch：

1. 校验每个 target 的 `record_ref`、独立 `expected_version`、owner 和 space；
2. 创建一个新的 Memory Canonical record；
3. 将每个输入 Memory 以新版本提交为 `memory_state=superseded`；
4. 任一 target 冲突、缺失、越权或无效时，整批不产生任何版本。

Merge 只提供 Application/Contract service 边界和测试，不新增公开 HTTP 路由。未来
Proposal API 必须复用相同的 target + expected version 结构。

### 3. Logical delete

Logical delete 以同一 Memory ID 创建新 Canonical version，Envelope 的
`record_state` 设置为 `logically_deleted`。它不把 Envelope `record_state` 与 Profile
`memory_state` 混为一个状态机。Active Memory list 默认排除该版本；旧 Candidate、旧
Index 和重复命令不得把它重新提交为 active head。

### 4. Physical erase

本切片不执行 physical erase。只冻结未来流程：阻止新派生读取，清除各 Adapter 的
敏感副本，最后以 `TombstonePayload` 提交 `record_state=erased`。Tombstone 只允许
`erased=true`、`erasure_ref` 和非敏感关系引用；失败或不可达组件不得伪造完成。
不新增 Erasure API、Job、Adapter 或数据库表。

### 5. Authority and authorization

用户 correction、merge、logical delete 命令经过验证后直接由 `CommitAuthority` 提交；
不新增 Proposal 持久化或审批表。所有写入要求 principal / space 与目标 Canonical
Envelope 的 owner / space 一致。读 ACL 和完整多用户权限推迟到 Phase 5。

### 6. HTTP surface

只实现现有 Contract 中的：

- `POST /v1/memories/{memory_id}/corrections`，带 Idempotency-Key、Expected-Version、
  X-Principal-Ref、X-Space-Id，成功返回 `200`；
- `DELETE /v1/memories/{memory_id}`，带相同写入边界，成功返回 `202`。

不新增 `/v1/memories/merges` 或其他临时 merge 路由。

## Error and replay contract

- `shadow.memory.not-found`：target 不存在；
- `shadow.memory.owner-space-mismatch`：principal / space 不匹配；
- `shadow.memory.head-not-active`：target 不是当前 active head；
- `shadow.memory.operation-invalid`：payload、target 数量或关系非法；
- `shadow.repository.expected-version-conflict`：CAS 版本冲突；
- `shadow.repository.idempotency-mismatch`：同 key 使用不同 request digest；
- `shadow.repository.unavailable`：Store 不可用。

相同 idempotency scope、key 和 request digest 只返回原 Commit 结果；任何失败批次都
不得留下部分 Canonical version。Store 不可用时不得返回持久成功。

## Consequences

### Positive

- Memory 稳定身份、版本和 Commit Authority 继续复用 Phase 0–1 原语；
- correction、merge 和 delete 的并发边界可由现有 CAS 和 restart fixture 验证；
- merge 不需要临时 HTTP 形状，避免未来 Proposal API 兼容负担；
- Physical erase 的敏感数据边界先冻结，避免错误地宣称已完成跨组件清除。

### Trade-offs

- 首个切片不能自动处理 source-dependent invalidation、Recall 或 Maintenance；
- Merge 在公开 API 中暂不可用，只能通过 Application/Contract service 使用；
- 读 ACL 仍是本地单用户边界，完整多用户授权延后 Phase 5。

## Acceptance evidence required before implementation

- correction、merge、logical delete 的 valid / invalid fixtures；
- 每个 merge target 独立 expected-version 的 all-or-nothing 测试；
- stable ID、旧版本不可变、deleted-head anti-resurrection、owner/space 拒绝测试；
- idempotent replay、Store unavailable、restart recovery 和 API status/error 测试；
- Tombstone schema/fixture 完整性验证，但不执行 physical erase；
- maintainer 明确接受本 ADR 后，才创建 Phase 2 implementation branch。
