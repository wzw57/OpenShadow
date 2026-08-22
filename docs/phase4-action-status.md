# Phase 4 Action 首片状态

状态：**已实现 / 已合并**

## 已接受

- [Phase 4 设计闸门](phase4-design-gate.md)
- [ADR-0015](adr/0015-phase4-action-lifecycle.md)
- Action、ActionProposal、ApprovalProposal、ProviderResult、Reconciliation Contract
- 通用 Proposal 写入边界和 Action 只读查询 Contract

## 已实现

- `ActionService` 与 Commit/CAS 生命周期；
- low-risk auto-approval、medium-risk approval-required、high-risk policy deny；
- deterministic Provider Adapter；
- Action Proposal/Approval/Provider Result/Reconciliation fixtures 的运行时验证；
- FastAPI Proposal dispatch 与 Owner/Space 隔离的 Action 查询；
- Action lifecycle、unknown、restart、Store outage、boundary 和 replay 测试。

## 后续切片

- Durable Outbox 已按 ADR-0016 实现并合并；状态见 [Phase 4 Durable Outbox](phase4-outbox-status.md)。
- Router/Policy Engine Adapter；
- Semantic Pulse；
- 跨组件 Erasure、encrypted Backup 内容和真实外部 Provider；
- cancelling/cancelled、高风险自动执行、Secret 读取。
