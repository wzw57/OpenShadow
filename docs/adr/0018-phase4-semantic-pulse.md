# ADR-0018：Phase 4 Semantic Pulse Proposal Producer 边界

- Status: Accepted
- Scope: Phase 4 Semantic Pulse 设计闸门
- Date: 2026-08-22

## Context

Semantic Pulse 可以用低成本规则或模型从 Event、Clock Observation 和 World State 中发现
需要用户注意的候选工作。但让 Pulse 直接写 Task、Memory、State 或 Action 会绕过 Admission、
Policy、Approval 和 Commit，也会让小模型成为系统正确性的隐性依赖。

## Decision

1. Pulse 是可选 Proposal producer，只能产生 Trigger、Observation 和 namespaced Proposal。
2. 每个 work-bearing Proposal 必须带 owner/space、evidence、budget、deadline、cooldown/dedup
   key 和 target input schema，并重新进入现有 Admission；Pulse 不拥有 Canonical authority。
3. `proposal_kind` 保持开放的 namespaced input family；Core/对应 Profile 决定 schema、capability、
   data scope、approval、expiry 和是否能 Commit。
4. Pulse source unavailable、budget exhausted、cooldown 或 unknown 时必须诚实返回状态；同一
   dedup key + digest 重放复用稳定 Proposal，不承诺跨进程 exactly-once。
5. 本 ADR 不引入通用后台 Job、Queue/Event Bus、Scheduler、HTTP 路由、真实 Provider 或 Secret。

## Consequences

- Pulse 可以被关闭、替换或延迟而不影响 TTL、恢复、Admission 或 Canonical integrity；
- 主动能力需要经过与用户命令相同的治理边界，避免“建议即执行”；
- 真正的周期调度、事件订阅、复杂预算和多租户配额需另建 capability-specific ADR。

## Revisit conditions

出现可测量的 Pulse 吞吐、跨设备触发或持久化冷却状态需求时，另建窄 Adapter/Store Capability，
不得通过本 ADR 引入通用 Job Platform。
