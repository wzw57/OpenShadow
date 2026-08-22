# ADR-0003: Tiny Kernel、Typed Profile 与 Capability-first Extension

- Status: Accepted — merged in Stage 4 PR
- Date: 2026-08-21
- Owners: OpenShadow maintainers

## Context

Stage 0–3 为长期资产、Memory、World State、Task、Execution、Adapter、Portability 和治理建立了完整模型。Stage 4 审查发现，Core 虽未实现外部算法，却承担了过多固定领域语义。

风险不是模块数量，而是 Shadow v1 自己的数据模型可能成为新的锁定：

- 五种 Execution Mode 容易变成永久封闭枚举；
- Memory、WorldState、Observation、Task、Action 容易成为 Kernel 硬编码类型；
- 所有 Adapter 共用巨大 Manifest 和 Result union；
- Durable Store Port 容易抽象整个数据库产品；
- 复杂 Policy、Event、Outbox 和 OperationJob 容易演化成自建平台。

同时，把所有对象降为无语义 `CanonicalObject + arbitrary JSON` 也不可接受，因为 Schema 不能独立保证状态转换、取消、现实副作用、任务连续性和语义迁移。

## Decision

### 1. Tiny Kernel

Kernel 只直接理解：

- Identity / Stable ID；
- Owner / Space；
- Canonical Envelope / Version / Lifecycle；
- Proposal / Validate / Commit；
- work-bearing Admission；
- Request / Run / Attempt；
- minimal Task continuity；
- Execution Binding / Capability；
- deterministic Policy enforcement；
- Migration / Export / Erasure Intent；
- Action safety minimum。

### 2. Typed Profile

Conversation、Memory、State、Durable Task、Action、Skill 和 Integration 由版本化 typed Profile 定义。

每个 Profile 声明：

- Profile Descriptor；
- payload and proposal schemas；
- lifecycle contract；
- validator；
- migration；
- portable export rules；
- compatibility。

Profile 属于 Shadow 的兼容承诺，但不通过永久 enum / switch 硬编码进 Kernel。Profile Validator 不获得 Commit 权限。

### 3. Proposal / Commit

所有 External Intelligence 和 Execution 只能产生 typed Proposal 或 Result。Shadow 执行 Schema、ExpectedVersion、Authority、deterministic Policy 和 Profile validation，再提交新 Canonical Version。

### 4. Extensible execution

ExecutionBinding 使用 namespaced `target_kind`。以下只是 well-known kinds：

- `shadow.agent-runtime`；
- `shadow.model-worker`；
- `shadow.deterministic-runner`；
- `shadow.workflow-target`；
- `shadow.capability-provider`。

新增 Target Kind 不修改 Core 主流程。Core 根据 Descriptor、Capability、Policy、数据边界、副作用、预算和健康校验。

### 5. Family Ports

公共 AdapterDescriptor 保持最小：

~~~text
adapter_id
adapter_family
contract_versions
capabilities
config_schema_ref
implementation_ref
health
~~~

Runtime 基础 Port 只要求 describe、execute、events；cancel、checkpoint、native resume、handoff、usage 和 reconciliation 是可选 Capability。

Execution / Intelligence Family 可以共享 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 和 Usage。Infrastructure Family 使用自己的 typed Result，仅共享 Message Envelope、Version、Correlation 和 structured error。

### 6. Store Capability split

不使用一个接口抽象整套数据库。Store Family 分为：

- Canonical Repository；
- Migration；
- Portable Export / Import；
- Backup / Restore；
- Durable Outbox；
- Integrity。

Adapter 只实现其声明的 Capability。

### 7. Narrow infrastructure semantics

- Domain Event 是通知，不要求 Event Sourcing；
- Outbox 只用于可靠跨边界副作用；
- OperationJob 只用于 export、import、migration、backup、erasure；
- 复杂 Policy Engine 外置，Core 只做最终确定性检查；
- State domain ontology、fusion 和 prediction 外置。

### 8. Classification

每个新概念必须先分类为：

- KERNEL；
- CONTRACT-ONLY；
- PROFILE / EXTENSION；
- LATER PHASE / DERIVED。

只有证明在未来 AI 范式变化后仍必须由 Shadow 直接理解的概念才能进入 KERNEL。

## Rationale

- Kernel lock-in 与 Runtime lock-in 同样危险；
- 统一 Envelope 保持资产治理一致；
- typed Profile 保留必要语义，不退化为 EAV / JSON blob；
- Proposal / Commit 让外部智能可升级而不获得主权；
- Capability-first Contract 支持未来未知 Target 和 Adapter；
- Store capability split 避免重造数据库平台；
- Profile migration 允许 Memory / State 分类未来变化而不重写 Kernel。

## Alternatives considered

### 保留当前固定领域模块

拒绝。长期会让 Kernel 随 Memory、State、Task 和 Adapter 生态膨胀。

### 完全通用 Canonical Object

拒绝。只能提供语法可移植性，无法保证状态不变量、取消真相、现实副作用和语义迁移。

### Event Sourcing 作为统一事实模型

拒绝。当前没有回放、审计或并发需求证明值得承担复杂度。Canonical Record 继续作为事实源。

### 通用 Plugin OS / Workflow / Policy Platform

拒绝。属于可替换外部能力，不是 Shadow 长期主权必需语义。

## Consequences

正面结果：

- Kernel 更小；
- Memory、State 和 Skill 可以独立升级；
- 新增 Target / Adapter 不改 Core 主流程；
- 数据库和 Runtime 只需实现实际 Capability；
- Proposal / Commit 成为稳定安全边界；
- 文档可以清楚区分 Shadow 产品能力与 Kernel 实现。

代价：

- 需要维护 Profile Registry、Validator 和语义 Migration；
- Contract Test 必须覆盖 Kernel 与各 Profile；
- 实现者不能把所有数据塞入任意 JSON；
- Profile 与 Kernel 的依赖方向需要持续检查；
- Capability Negotiation 比固定接口需要更多测试。

## Revisit triggers

- 某项跨 Profile 不变量无法通过当前 Kernel 执行；
- Profile Validator 成为不可信代码且当前隔离不足；
- namespaced target kind 无法表达真实执行目标；
- Capability Negotiation 无法接入主要外部项目；
- Profile Migration 无法维持标准导出；
- 性能测量证明 Profile validation 成为不可接受瓶颈。

重新评估必须通过新 ADR，不得通过 Kernel 私有类型分支绕过本决定。
