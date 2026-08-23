# ADR-0029：Production Voice、Device 与 Integration Adapter Boundary

- Status: Accepted / implementation authorized
- Date: 2026-08-23
- Deciders: OpenShadow maintainers
- Related: ADR-0015、ADR-0016、ADR-0019、ADR-0026、ADR-0027

## Context

语音、硬件和外部 Integration 可能触发现实副作用并携带敏感数据。若把 provider SDK、
麦克风、webhook 或 token 逻辑放进 Kernel/Application，会绕过 Capability、Consent、
Admission 和 CommitAuthority。

## Decision

定义 Vendor-neutral Adapter Port：外部组件只返回 Result/Observation，写入仍经过现有
Action/Outbox/Commit 边界。每次调用检查已验证主体、Space/endpoint scope、capability、
consent、expiry/revocation 与 data classification；secret 只以 opaque reference 传递。
首片只交付 deterministic Contract Adapter 和测试，不连接真实硬件、语音服务或 OAuth。

## Consequences

- 真实 Provider 可替换，Core 不知道 Vendor 私有协议；
- unknown/failed 结果可审计且不被自动重试成重复副作用；
- UI 只能展示通用状态，不会成为设备或 Provider 控制面。
