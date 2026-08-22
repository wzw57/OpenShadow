# Phase 2 第五切片状态：SkillAsset sidecar

状态：**已实现 / 已合并**

设计闸门：[phase2-skillasset-design-gate.md](phase2-skillasset-design-gate.md)；ADR：
[0009](adr/0009-phase2-skillasset-sidecar.md)。

## 已交付

- `SkillBundleManifest`、`SkillBundleFile` 与 `shadow.skill-bundle-digest.v1` 确定性
  manifest/digest 计算；拒绝绝对路径、traversal、符号链接、重复规范化路径和空 Bundle；
- `SkillAssetRegistrationRequest` / `SkillAssetRegistrationResult`；
- `SkillAssetService.register` 的 create / refresh；refresh 保持稳定 skill identity，要求
  expected version 并通过 Owner/Space 检查；
- Canonical `shadow.profile.skill-asset` sidecar 通过现有 CommitAuthority/CAS 写入，
  idempotency replay 不产生新 version，replay digest 稳定；
- digest 篡改、schema、owner/space、version conflict、Store unavailable 和 restart
  证据；standard Bundle 内容未被修改，`allowed-tools` 没有 Capability grant；
- Contract fixtures：minimal/complete/allowed-tools、digest 变化、有效/无效 sidecar。

## 验收证据

- `tests/test_phase2_skillasset.py`：11 项通过；
- Documentation Drift 测试确认本切片没有新增 HTTP、数据库表、Proposal、Provider upload
  或脚本执行；
- Ruff、全量 pytest、隔离 SQLite migration upgrade/downgrade 与 PR CI 均通过。

## 明确未实现

- Provider Skill API、Runtime projection、安装/卸载执行和脚本 Sandbox；
- SkillAsset logical delete/physical erase、Portable Import/restore、Backup 清除；
- Integration / Secret / MCP / Executable 绑定和完整多用户 ACL；
- 新增 Skill HTTP API 或独立 Skill Store。

下一步必须先通过 Integration 设计闸门；未获接受前继续只维护文档。
