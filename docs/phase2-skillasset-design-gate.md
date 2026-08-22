# Phase 2 第五切片设计闸门：SkillAsset 与 Agent Skills sidecar

状态：**Accepted / Phase 2 第五切片获准实现**

本文件在 [ADR-0004](adr/0004-agent-skills-compatibility.md) 的标准兼容决定之上，
冻结第一个 SkillAsset 实现切片。它只授权 sidecar 注册、确定性 bundle manifest/digest
校验和 Canonical Commit；不授权 Provider 上传、脚本执行、Runtime projection、Integration
或新的 HTTP/数据库能力。

维护者“按照开发流程继续推进，直到完成 Phase 2”的授权作为本闸门的接受依据。若实现
发现需要扩大下列边界，必须先更新本文件和 ADR，再继续编码。

## 已决定内容

### Canonical 与标准 Bundle 边界

- `SKILL.md`、`scripts/`、`references/`、`assets/` 保持原样；Shadow 不向 Bundle 写入
  sidecar 字段，也不修改文件内容。
- Canonical record type 为 `shadow.profile.skill-asset`，typed payload 使用现有
  `SkillAssetPayload` schema；`skill_id` 是稳定资产身份，record version 是治理版本。
- sidecar 至少保存 `source_ref`、`pinned_revision` 或 `snapshot_artifact_ref` 之一、
  `bundle_digest`、`trust`、`permission_policy_ref`、`data_classification`、
  `install_state`、`runtime_projection_refs` 和 `provider_external_refs`。
- Provider ID、Runtime prompt、索引、安装缓存都是 Derived/External reference，丢失后
  可从 Canonical sidecar 与 Bundle 重建；本切片不调用 Provider。

### 注册与刷新 Contract

`SkillAssetService.register` 接受一个已由用户或受信 Adapter 产生的注册命令：

- `principal_ref`、`space_id`、`skill_id`、`source_ref`；
- `pinned_revision` 与 `snapshot_artifact_ref` 至少一个；
- `bundle_root`（Application 内部输入）和声明的 `bundle_digest`；
- `trust`、`permission_policy_ref`、`data_classification`、`install_state`；
- 去重后的 runtime/provider refs；
- `operation=create|refresh`、refresh 时的 `expected_version`、`idempotency_key`。

Service 按 `shadow.skill-bundle-digest.v1` 递归枚举普通文件，拒绝绝对路径、`..`、符号
链接和重复规范化路径，按 POSIX 路径排序后计算 manifest 与 SHA-256。声明 digest 不匹配
时拒绝提交。标准 Bundle 的 frontmatter/目录规范由 Agent Skills validator 负责；本切片
不执行脚本、不授予 `allowed-tools` 权限。

`create` 使用稳定 `skill_id` 对应的 record identity；`refresh` 在同一 record_id 上创建
新 Canonical version，必须匹配 `expected_version`，Owner/Space 不可改变。首次发现的
资产默认可以是 `trust=untrusted`；`allowed-tools` 永远不能直接产生 CapabilityEnvelope。

### Authority、原子性与重放

- 注册和刷新都通过现有 `CommitAuthority` + `CommitPlan`；Service/Adapter 不得直接写
  Repository。
- 相同 scope/key/request digest 的 replay 返回原 commit 和稳定 record/version，不创建
  新版本；同 key 不同请求返回 `shadow.skill-asset.replay-conflict`。
- refresh 的 expected-version 冲突返回结构化 `shadow.skill-asset.version-conflict`，不
  写入半成品；Store unavailable 返回 `shadow.repository.unavailable`，不声称成功。
- owner/space 不匹配返回 `shadow.skill-asset.owner-space-mismatch`；manifest、digest、
  schema 或 ref 不合法返回 `shadow.skill-asset.invalid`。
- 不新增 Proposal 表、审批流、HTTP 路由、数据库表、Outbox 或 OperationJob；用户命令
  直接验证后 Commit。

### 敏感数据与恢复

- Canonical sidecar 只保存 Bundle 的引用、digest 与治理元数据，不把敏感原文或脚本输出
  写入 typed payload。
- `snapshot_artifact_ref` 只是可验证 immutable snapshot 的引用；本切片不实现上传、复制、
  Portable Import/restore 或 Physical erase。
- digest 变化必须导致新 version/显式冲突，不得继续复用旧 trust 或高风险权限断言。
- old sidecar version、Derived projection 和旧导出不能把已不存在的 Bundle 当成当前内容；
  anti-resurrection 与删除/擦除语义由后续 Erasure/Import 闸门负责。

## 结构化结果与验收证据

实现必须提供可验证的 `SkillAssetRegistrationResult`（committed、replayed、conflict、
invalid 或 unavailable）、record/version 引用、bundle digest 和 result digest。Contract
fixtures/tests 至少覆盖：

- minimal/complete/allowed-tools-untrusted Bundle 的确定性 digest；
- 路径穿越、符号链接、重复路径、digest 篡改和 sidecar schema 拒绝；
- create、refresh expected-version、owner/space mismatch、replay/replay-conflict；
- refresh 只产生一个新 version，旧 Bundle/sidecar 不可变；
- Store unavailable 不声称成功，restart 后 sidecar version/digest 可恢复；
- `allowed-tools` 不产生 Capability grant，Provider/Runtime refs 不触发外部副作用；
- Documentation Drift 确认无新 HTTP、表、Proposal、Provider upload 或脚本执行。

## 明确不在本切片

- Provider Skill API、Runtime Projection、安装/卸载执行和脚本 Sandbox；
- SkillAsset logical delete/physical erase、Portable Import/restore、Backup 清除；
- Integration Profile、Secret 管理、MCP/Executable 绑定和完整多用户 ACL；
- 新增 Skill HTTP API 或独立 Skill Store。

## 闸门结论

本闸门已接受，允许创建 `phase2/skillasset-implementation` 分支。实现完成后才可进入
Integration 设计闸门；所有未列出的能力继续只维护文档。
