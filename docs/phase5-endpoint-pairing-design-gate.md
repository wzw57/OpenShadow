# Phase 5 Endpoint Pairing / Device Trust 设计闸门

状态：**Proposed / 等待维护者接受**

本闸门是 Phase 5 第一个独立切片，只冻结 Endpoint Profile、pairing proposal 和 Admission
trust context。它不实现多用户 ACL、共享 Space、远程同步、Voice 或真实设备协议。

## Endpoint Profile

- Record type：`shadow.profile.endpoint`，继续使用 Canonical version rows、CommitAuthority、
  Owner/Space 和 CAS；不新增数据库表。
- `endpoint_kind` 使用 namespaced open-world contract（例如 `shadow.web`、`shadow.mobile`、
  `shadow.voice`），不把设备类型永久封闭在 Kernel enum。
- `trust_state` 为 `pending`、`proof-required`、`trusted`、`revoked`；`status` 为 `online`、
  `offline`、`unavailable`。revoked Endpoint 不能通过 Admission 创建新工作。
- 只保存 `public_key_ref`、`pairing_ref`、capability refs、last_seen 和审计证据；不保存私钥、
  pairing code、token、Secret、音频原文或设备本地 session。

## Pairing flow

1. 用户命令或受信任现有 Endpoint 提交 namespaced EndpointPairingProposal；
2. Core 校验 principal/space、过期时间、proof method、设备 descriptor 和 idempotency；
3. Pairing Adapter 只返回 proof/observation，不能直接创建 Endpoint；
4. Core 在一个 CommitPlan 中创建 Endpoint pending/trusted head 和 pairing audit record；
5. revoke 是同一 Endpoint 的新版本，旧 Admission context、旧 proposal 和重复命令不能复活它。

本切片不新增 Endpoint 专用 HTTP 路由；若需要写入，复用通用 Proposal/Admission boundary。

## 错误、原子性和重放

结构化错误至少包括：`shadow.endpoint.not-found`、`shadow.endpoint.unauthorized`、
`shadow.endpoint.proof-invalid`、`shadow.endpoint.expired`、`shadow.endpoint.revoked`、
`shadow.endpoint.capability-unsupported`、`shadow.repository.expected-version-conflict`、
`shadow.repository.idempotency-mismatch` 和 `shadow.repository.unavailable`。

相同 `endpoint:{principal}:{space}:{idempotency_key}` + digest 重放复用稳定 Endpoint/Pairing
引用，不创建第二个 Endpoint 或 Admission；不同 digest 返回结构化冲突。Store unavailable
时不声称 pairing/trust 成功。

## Design-only 禁止事项

- 不新增设备注册表、Session 表、ACL 表、同步队列、远程 Store、Voice Provider 或公开路由；
- 不读取/保存 Secret、私钥、pairing code、token、原始音频或设备私有状态；
- 不让 Endpoint 绕过 Admission，不把 Endpoint ID 当作 owner_ref，不自动共享个人资产。

## 评审与实现闸门

设计阶段只提交本文件、[ADR-0020](adr/0020-phase5-endpoint-pairing.md)、Endpoint Schema、
fixtures、documentation-sync 和静态测试。维护者接受后才创建
`phase5/endpoint-pairing-implementation` 分支；实现必须通过全量 pytest、Ruff、Alembic
upgrade/downgrade 和 `git diff --check`。
