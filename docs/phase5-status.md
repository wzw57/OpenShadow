# Phase 5 实现状态

状态：**已实现 / Core Slice 已完成**

更新时间：2026-08-23

## 本切片

- Endpoint pairing / revoke；
- Space 创建与查询；
- owner/editor/viewer membership；
- 一次性邀请、接受、撤销和过期；
- Space 级查询 ACL 与单用户 local-dev 兼容；
- Web UI context 切换和成员管理。

## 验收证据

- `IdentityService` 使用现有 Canonical version rows、CommitAuthority 和 CAS；无新增迁移或
  SQL 表；
- Endpoint pair/revoke、Space 创建/查询、邀请接受/撤销、owner/editor/viewer ACL 和
  local-dev compatibility 有 API 测试；
- Web UI 已提供 Space/Endpoint context、pair、Space 创建、邀请、接受和成员撤销入口；
- `pytest -q`：247 passed；Ruff、OpenAPI YAML、offline fixtures、Alembic upgrade/downgrade
  和 Chromium smoke 均通过。

## 仅 Contract-only

- OAuth/OIDC、密码找回和生产级 token issuer；
- Voice/STT/TTS/wake-word；
- 远程 Store、离线同步和跨设备冲突合并；
- 分布式音频。

这些能力不得在本切片中通过临时表、通用 Queue 或 Vendor 分支提前实现。
