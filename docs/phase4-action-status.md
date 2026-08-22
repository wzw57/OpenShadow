# Phase 4 Action 首片状态

状态：**设计闸门 Accepted；实现尚未开始**

## 已接受

- [Phase 4 设计闸门](phase4-design-gate.md)
- [ADR-0015](adr/0015-phase4-action-lifecycle.md)
- Action、ActionProposal、ApprovalProposal、ProviderResult、Reconciliation Contract
- 通用 Proposal 写入边界和 Action 只读查询 Contract

## 待实现

- `ActionService` 与 Commit/CAS 生命周期；
- deterministic Provider Adapter；
- Action Proposal/Approval/Result/Reconciliation fixtures 的运行时验证；
- FastAPI Proposal dispatch 与 Action 查询；
- Action lifecycle、unknown、restart、Store outage 和 replay 测试。

## 明确未实现

- Durable Outbox；
- Router/Policy Engine Adapter；
- Semantic Pulse；
- 跨组件 Erasure、encrypted Backup 内容和真实外部 Provider；
- cancelling/cancelled、高风险自动执行、Secret 读取。
