# ADR-0020：Phase 5 Endpoint Pairing 与 Device Trust 边界

- Status: Proposed
- Scope: Phase 5 Endpoint pairing / device trust 首片
- Date: 2026-08-22

## Context

Phase 5 需要让 Web、Mobile、Voice 和设备端继续使用同一个 Shadow，但 Endpoint session 不能
代替 Principal、Owner/Space 或 Admission。Pairing 还会接触 proof、public key 和设备能力，
这些内容不能直接进入普通 Canonical payload。

## Decision

1. Endpoint 使用 `shadow.profile.endpoint` typed Profile；pairing 使用通用 Proposal/Admission
   boundary，不新增 Endpoint 专用路由或表。
2. Endpoint `endpoint_kind` 为 namespaced open-world；`trust_state` 显式区分 pending、
   proof-required、trusted、revoked。revoked Endpoint 不能创建新工作。
3. Pairing Adapter 只能返回 proof/Observation；Core 校验 owner/space、expiry、capability、
   idempotency，并通过 Commit 创建或更新 Endpoint。
4. 只保存 opaque proof/public-key refs；不保存 Secret、私钥、token、pairing code、音频或
   Provider 私有状态。revoke 使用 CAS 新版本，旧 context 和重复命令不能复活 Endpoint。
5. 多用户 membership/ACL、共享 State、同步和 Voice 必须另建 ADR；本 ADR 不定义它们的读权限。

## Consequences

- 单用户本地部署仍可只使用一个 trusted Web Endpoint；
- 增加设备不会改变个人资产所有权；
- Endpoint 被撤销后，Admission 可确定性拒绝新工作，而不依赖设备在线；
- 真实安全硬件、密钥托管和设备协议保持在 Adapter capability 外部。

## Revisit conditions

需要跨设备密钥轮换、硬件证明、离线恢复或多用户邀请时，分别建立 capability-specific ADR，
不通过本 ADR 引入 ACL 或同步平台。
