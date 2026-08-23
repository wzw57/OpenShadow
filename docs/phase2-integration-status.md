# Phase 2 第六切片状态：Integration Profile

状态：**已实现 / 已合并**

设计闸门：[phase2-integration-design-gate.md](phase2-integration-design-gate.md)；ADR：
[0010](adr/0010-phase2-integration-profile.md)。

## 已交付

- `IntegrationPayload` schema 已纳入离线 Contract Registry；
- `IntegrationRegistrationRequest` / `IntegrationRegistrationResult` 与
  `IntegrationService.register` create / refresh；
- 稳定 integration identity、Owner/Space、expected-version、CAS 和 idempotency replay；
- Adapter descriptor digest、config/secret/health references、status 与 lifecycle 的
  Contract 验证；
- `secret_refs` 只保存 StableRecordRef，绝不保存 secret material；
- external_ref secret-material 拒绝，Canonical payload 不保存 token/password/private key；
- Store unavailable、version conflict、owner/space mismatch、restart、旧版本不可变和
  needs_reauth/unavailable 状态证据；
- valid/invalid Integration fixtures 与 Documentation Drift 检查。

## 验收证据

- `tests/test_phase2_integration.py`：至少 10 项；
- 全量 Ruff、pytest、隔离 SQLite migration upgrade/downgrade 和 PR CI 通过。

## 明确未实现

- Provider/OAuth/PKCE/webhook/网络 health probe、Secret vault 与 token rotation；
- Runtime/Model/Runner Binding、CapabilityEnvelope、MCP/Executable 执行；
- Integration logical delete/physical erase、Portable Import/restore、Backup 清理；
- 新增 Integration HTTP API、数据库表、Proposal/Outbox/OperationJob 和完整 ACL。

Portable Import/restore 与 Physical erase 后续切片已分别通过设计闸门并合并；本切片仍不
提供 Provider/OAuth 或 Secret vault 实现。
