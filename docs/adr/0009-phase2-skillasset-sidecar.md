# ADR-0009: Phase 2 SkillAsset sidecar 注册边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

ADR-0004 已确定 Shadow 原生兼容 Agent Skills Bundle，并用独立 sidecar 保存所有权、
digest、trust、permission 和 projection 引用。Phase 2 需要先交付一个不会污染标准
Bundle、也不会把 Provider 状态误当 Canonical 事实的最小纵向切片。

## Decision

1. SkillAsset 的 Canonical record type 为 `shadow.profile.skill-asset`，使用现有
   `SkillAssetPayload` schema；`skill_id` 保持跨 version 稳定，refresh 只追加 Canonical
   version。
2. 注册命令必须绑定 `principal_ref`/Owner、`space_id`、source reference 和 immutable
   `pinned_revision` 或 `snapshot_artifact_ref`，并声明 `bundle_digest`。
3. Application Service 在 Commit 前执行 `shadow.skill-bundle-digest.v1` 的离线 manifest
   校验：只接收普通文件，拒绝 traversal、绝对路径、符号链接和重复路径；按 POSIX 路径和
   原始 bytes 计算确定性 digest。
4. create 使用稳定 asset identity；refresh 必须带 expected version 并经 Owner/Space
   校验。所有写入通过现有 CommitAuthority/CAS，复用现有 idempotency scope。
5. 同 key 同 digest replay 返回原结果；同 key 不同 request、digest mismatch、Owner/Space
   mismatch、version conflict 和 Store unavailable 都返回结构化错误，不产生部分提交。
6. `allowed-tools` 只是 Bundle 提示，不能授予 CapabilityEnvelope；trust/permission
   绑定到具体 digest/revision，digest 改变必须重新注册/审查。
7. 本 ADR 只交付 sidecar Contract、Application Service、deterministic fixtures/tests；
   不新增 HTTP、表、Proposal、Provider upload、Runtime projection、脚本执行、Import 或
   Erasure。

## Rationale

以 Canonical sidecar 保存最小治理事实，既能保持标准 Bundle 的可移植性，又能让 Provider
和 Runtime 状态可删除、可重建。digest/CAS/idempotency 让 refresh 可审计且不会因并发或
重放产生幽灵版本。

## Alternatives considered

- 把 Shadow 字段写进 `SKILL.md`：破坏标准 Bundle，拒绝。
- 只保存 Provider Skill ID：Provider 状态不可恢复，拒绝。
- 让 `allowed-tools` 直接授予能力：绕过 Shadow Authority，拒绝。
- 先做 Provider upload 或脚本执行：扩大副作用边界，延后到后续 Integration/Projection
  闸门。

## Consequences

- SkillAsset 可在不同 Runtime/Provider 间迁移，Canonical 事实不依赖外部对象。
- refresh 会产生可验证的新 version；Derived projection 需要单独重建。
- Bundle snapshot 的实际存储、删除和跨设备恢复仍需要 Portable/Erasure 设计。

## Revisit triggers

- Agent Skills 规范出现不兼容变化；
- digest 无法表达新的 Bundle 语义或需要签名；
- Provider/Runtime projection 无法从 sidecar 和 immutable source 重建；
- 用户需要 SkillAsset ACL、删除或导入语义超出本 ADR。
