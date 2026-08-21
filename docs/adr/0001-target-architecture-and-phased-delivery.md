# ADR-0001: 完整目标架构与分阶段实现

- Status: Proposed — pending final PR review and merge
- Refined by: [ADR-0003](0003-tiny-core-and-typed-profiles.md)
- Date: 2026-08-21
- Owners: OpenShadow maintainers

## Context

OpenShadow 需要在多年使用中持续替换 Runtime、模型、Memory Intelligence、数据库、Runner、Router、语音和设备能力，同时保持用户资产、任务、记忆和现实状态连续存在。

只设计第一条 MVP 链路会使未来能力被迫绕过旧模型；一次实现全部模块又会造成不必要复杂度。需要区分完整逻辑架构与当前实现范围。

## Decision

Shadow 的完整逻辑架构由以下责任平面组成：

- Interaction；
- Access & Admission；
- Tiny Kernel；
- Execution；
- Adapter Control；
- Canonical State；
- Replaceable Infrastructure；
- External Implementations and Sources。

所有承载工作的输入和触发统一经过 Admission；健康、只读控制面查询和已有 Run 订阅不创建 Root Run。所有执行使用 Run、Execution Binding 和 Execution Attempt。

Binding 使用可扩展 namespaced `target_kind`。agent-runtime、model-worker、deterministic-runner、workflow-target 和 capability-provider 是首批 well-known kinds，不是封闭全集。

Shadow Tiny Kernel 持有 Identity、Canonical Envelope、Proposal / Commit、Run / Attempt、minimal Continuity、Binding 和用户控制。Memory、State、Task、Action、Skill 等领域语义使用 typed Profile。Execution / Intelligence 与 Infrastructure Port 使用 family-specific Contract。

完整目标架构先冻结，按照 Phase 0–5 逐步实现。Phase 标签只表示实现顺序，每个 Phase 必须是同一目标架构的真子集。

默认部署从模块化单体开始。只有安全隔离、资源调度、故障隔离、多设备或已验证吞吐需求出现时才拆分进程或服务。

## Rationale

- 用户长期资产不能依赖某个快速变化组件的私有格式；
- Capability-first 执行模型允许当前与未来 Target 共存；
- 完整边界避免后续建立旁路；
- 分阶段实现避免为未验证用例提前构建微服务和复杂基础设施；
- 逻辑架构与部署拓扑分离，允许低成本起步和长期演进。

## Alternatives considered

### 只设计 MVP

拒绝。会把当前实现限制误当作长期边界，增加未来数据与接口迁移成本。

### 一次实现完整系统

拒绝。会提前承担 Router、Action、World State、多用户、语音和分布式系统复杂度。

### 从微服务开始

拒绝。当前没有独立伸缩、隔离或团队边界证据。

### 所有任务都交给 Agent Runtime

拒绝。确定性程序、单次模型调用、工作流和外部动作不应被迫进入 Agent Loop。

## Consequences

正面结果：

- Canonical Identity 和 Authority 从第一版稳定；
- 后续能力通过 Port、Capability 和 Adapter 增加；
- 部署可以从单进程演进到隔离 Worker 和多设备；
- Workflow、Router、Pulse 和多用户不会阻塞首批开发。

代价：

- 第一版必须保留 owner_ref、space_id、schema_ref、Binding 和 minimal AdapterDescriptor 等基础字段；
- 需要维护跨语言 Schema 与 Contract Test；
- External Component 不能直接写数据库，增加一层边界映射；
- 每个 Phase 都需要验证没有绕过完整架构。

## Revisit triggers

仅在以下证据出现时重新评估：

- 某类权威状态无法由当前 Core 边界表达；
- namespaced target_kind 与 Capability 无法覆盖真实执行类型；
- 模块化单体无法满足已测量的可靠性或隔离需求；
- Profile / Adapter Capability Negotiation 无法支持主要外部项目；
- 多用户或多设备需求要求改变 Owner / Space 的事实所有权。

重新评估必须新增 ADR，不能通过实现旁路悄悄改变架构。
