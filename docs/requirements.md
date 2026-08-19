# OpenShadow 需求基线

**状态：前期需求对齐 / 待核心契约冻结**  
**目标：OpenShadow v0.1 MVP**

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

## 1. 产品定义

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它负责持有必须跨模型、跨 Runtime、跨设备、跨 Session 和跨时间持续存在的规范化个人资产，并让 Runtime、Memory Engine、Skill 执行机制、Capability Provider 和工具协议可以被替换、升级和迁移。

OpenShadow 不以“成为最聪明的 Agent”为目标，也不重造已有成熟 Runtime、Browser Agent、Coding Agent、Skill Execution Engine、Memory Engine 或设备平台。

## 2. 核心原则

### 2.1 资产所有权原则

> **Shadow 可以依赖外部生态提供实现，但不能依赖外部生态持有规范化个人资产。**

### 2.2 核心边界原则

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余功能优先复用外部成熟系统。**

### 2.3 外部格式原则

外部格式只允许作为：

- Import；
- Export；
- Adapter；
- Projection；
- Derived View。

外部格式不能直接成为 Shadow 核心事实源。

## 3. Shadow 不是 Memory Engine

Memory 只是 Shadow 的一个子系统。

即使 Memory 子系统暂时不可用，Shadow 仍必须能够：

- 创建、保存、暂停、恢复 Task；
- 保存 Semantic Checkpoint；
- 在不同 Runtime 间接力 Task；
- 持有 Canonical Skill 并同步 Runtime Projection；
- 管理 Capability / Policy / Approval / Execution Ledger；
- 接收 Event、维护 World State、执行 Scheduler；
- 保存 Artifact、历史和副作用状态。

如果移除 Memory 后这些能力无法存在，则说明系统边界发生错误退化。

## 4. 核心一等对象

| 对象 | 定义 |
| --- | --- |
| **Identity** | 用户身份、长期偏好、信任与隐私基线 |
| **Event** | 已发生事实的持久记录 |
| **World State** | 当前世界状态的紧凑投影 |
| **Task** | 需要持续完成的工作及其状态 |
| **Memory** | 对历史证据形成的可追溯、可修正认知 |
| **Skill** | 可复用的方法、经验和程序性知识 |
| **Capability** | 稳定、可治理、可版本化的动作或查询契约 |
| **Policy** | 权限、风险、隐私、预算与审批规则 |
| **Artifact** | 文件、报告、日志、工具结果等任务产物 |
| **Runtime Binding** | 当前执行 Runtime 与临时 Session 引用 |

基本语义：

```text
Task        = 我现在要完成什么
Memory      = 我知道什么
Skill       = 这类事情应该怎么做
Capability  = 系统实际上能做什么
Policy      = 哪些行为被允许
```

## 5. Task 与 Semantic Checkpoint 需求

- Task 必须由 Shadow 持有，Runtime Session 不得作为唯一事实源；
- Task 必须保留目标、阶段、已完成工作、已知事实、决策、Artifact、剩余工作、权限与副作用状态；
- Runtime 中断或替换后，Task 必须能从最近持久化 Semantic Checkpoint 恢复；
- Shadow 不要求迁移隐藏思维链、KV Cache 或 Runtime 私有 Planner 状态；
- 跨 Runtime 接力最低保证：Task 语义、证据、产物、剩余工作和副作用状态不丢失。

## 6. Memory 需求

### 6.1 三层数据模型

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- Raw Evidence 是长期证据源；
- Canonical Memory 必须可修正、可追溯、支持时间有效性；
- embedding、向量索引、摘要和图等派生结果必须可重建；
- Memory Engine 不能成为 Canonical Memory 的唯一事实源。

### 6.2 召回

- Recall 应围绕当前 Task 的决策需要；
- 可以通过 Memory Broker / Context Compiler 提供任务相关 Memory；
- 具体检索引擎、向量库和图实现必须可替换；
- Canonical Memory 不足时可以回到 Raw Evidence、历史 Task 与 Artifact。

V0.1 不要求冻结复杂 Memory Router 策略。

## 7. Skill 需求

### 7.1 Skill 所有权边界

Skill 是 Shadow 的一等长期资产，但**Skill 的具体执行编排不属于 Shadow 稳定核心**。

核心规则：

> **Shadow controls availability; Runtime controls activation.**

Shadow 决定某个用户 / Runtime / Task 可以使用哪些 Skill；Runtime 决定本次执行中何时发现、加载、激活和组合这些 Skill。

### 7.2 Shadow 必须持有的 Skill 信息

至少包括：

- Canonical Skill identity；
- Raw Skill Source；
- Version；
- Provenance；
- Trust / Security metadata；
- Enable / Disable / Scope；
- Runtime compatibility；
- Runtime Projection / Sync records；
- Import / Export / Migration / Rollback 元数据。

### 7.3 Runtime 负责的 Skill 能力

优先交给 Runtime：

- Skill discovery；
- Skill activation；
- progressive disclosure；
- Skill composition / orchestration；
- Runtime-native bundle / prompt / reference 加载；
- Runtime 内部 Tool 使用策略。

Shadow V0.1 不自研这些机制。

### 7.4 Runtime Projection

Runtime-specific Skill 表示必须视为可删除、可重建派生资产：

```text
Raw Skill Source
      ↓
Canonical Skill
      ↓ Runtime Skill Adapter
Runtime Projection
      ↓
Runtime
```

Runtime 不得直接修改 Canonical Skill Store。

如果 Runtime 新建或修改 Skill，应进入：

```text
Runtime Change
→ Skill Candidate / Change Event
→ Shadow Import / Review / Normalize
→ Canonical Skill update
```

### 7.5 可插拔 Skill Manager

Skill Manager 可以作为未来独立扩展组件，用于：

- 高级 Skill 检索；
- Skill 关系 / Graph；
- 冲突处理；
- 路由；
- 自动评估与演化。

但必须满足：

- 不持有 Canonical Skill 唯一事实源；
- 可以整体替换；
- 升级失败不破坏 Canonical Skill；
- 不绕过 Runtime / Capability / Policy 边界。

因此 V0.1 **不要求** SkillNeed、Skill Resolver、SkillBundle、Skill Graph Executor 或自研 Progressive Disclosure Engine。

## 8. Capability、Provider 与协议需求

### 8.1 Capability

Capability 表示稳定、可治理的动作或查询契约，例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

Capability 必须独立于具体 Provider 和 Transport。

### 8.2 Provider

Provider 是 Capability 的实际实现者。Provider 可以替换，但 Capability 语义应尽量稳定。

### 8.3 Tool 与 MCP

必须明确区分：

> **Tool 是接口；Capability 是长期能力资产；Skill 是可复用经验；MCP 是协议。**

- MCP Tool 可以映射为 Capability Candidate 或 Provider Binding；
- MCP Resource 可以成为 Context / Evidence Source；
- MCP Prompt 可以成为 Skill Candidate 或 Runtime Template；
- 使用 MCP 不得绕过 Capability Gateway / Policy / Execution Ledger。

## 9. Runtime 与 SRI 需求

- Runtime 是可替换执行器；
- Shadow 通过 SRI 统一执行、恢复、暂停、取消、检查点、状态、能力发现和健康检查；
- 至少支持两个不同 Runtime Adapter 以验证 Runtime-neutral；
- Runtime-native Session 只作为 Binding，不作为 Task 事实源；
- Runtime 切换通过 Shadow 规范化状态重新 hydrate；
- Runtime Adapter 必须可独立替换升级。

## 10. Event、World State 与持续运行需求

- Event 采用 append-oriented 方式持久记录；
- World State 由 Event 投影生成；
- Task 可以由 User、Event、Schedule 或 Condition 触发；
- 删除 Chat UI 后系统仍应能接收 Event、维护状态、恢复 Task 并执行允许的动作；
- Pulse / 小模型分层属于实现优化，不属于核心所有权原则。

## 11. Capability Gateway 与治理需求

所有现实副作用统一经过：

```text
Identity
→ Schema Validation
→ Policy / Risk
→ Approval when required
→ Idempotency
→ Provider
→ Execution Ledger / Audit
```

必须保证：

- Runtime 不直接持有长期 raw secrets；
- 高风险 Capability 支持 Approval；
- 每个副作用动作有稳定 action_id / idempotency_key；
- Runtime crash / retry 不重复执行已完成动作；
- Runtime 原生 MCP / Tool Calling 不能绕过 Gateway。

## 12. Context Compiler 需求

Context Compiler 负责把 Shadow 规范化资产转换为当前 Runtime 可以消费的上下文。

可能包括：

```text
Task / Checkpoint
Relevant Memory
Available Skill refs / projections
World State
Policy / Trust Profile
Allowed Capabilities
Artifact / Evidence refs
```

Context Compiler 不负责替代 Runtime 的 Skill 激活或 Agent Loop。

## 13. 可替换组件升级需求

下列组件必须通过稳定边界接入：

- Runtime；
- Memory Engine；
- Skill Manager；
- Runtime Skill Adapter；
- Provider；
- MCP / Protocol Adapter；
- Search / Index Engine。

升级目标：

> **新技术主要替换 Adapter、Manager 或派生表示，不迁移规范化个人资产。**

## 14. 非功能需求

| 维度 | 要求 |
| --- | --- |
| 本地优先 | Raw Evidence、Canonical Memory、Policy、Canonical Skill 默认本地持有 |
| 可移植性 | 核心数据不依赖单一 Runtime / Provider / Skill 格式 |
| 可审计性 | 重要状态、Skill 来源和现实动作可追溯 |
| 可恢复性 | Core 重启不丢 Task / Event / Ledger；Runtime crash 可恢复 |
| 可升级性 | Runtime / Skill Adapter / Manager / Provider 具有清晰替换边界 |
| 最小权限 | Runtime 与外部 Provider 只获得所需数据与权限 |
| 可重建性 | 派生索引、Runtime Projection 可以重新生成 |

## 15. v0.1 范围

### 必做

- Event / World State；
- Task / Semantic Checkpoint / Artifact；
- Raw Evidence / Canonical Memory 基础闭环；
- Skill Store / Version / Provenance / Trust / Runtime Projection / Sync；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Execution Ledger；
- SRI + 至少两个 Runtime Adapter；
- Context Compiler；
- Scheduler / Event-driven execution；
- PostgreSQL 单机持久化；
- CLI / 最小管理入口。

### 暂不做

- 自研 Agent Loop；
- 自研 Skill Resolver；
- Skill Graph Executor；
- Progressive Disclosure Engine；
- 完整 Workflow Engine；
- 自研 Browser Agent / Coding Agent；
- 自研 Vector DB / Graph DB；
- Plugin Marketplace；
- 完整 IM / Voice 平台；
- Multi-user SaaS；
- Kubernetes / 复杂微服务。

## 16. v0.1 验收场景

| 场景 | 通过条件 |
| --- | --- |
| Runtime Continuity | Runtime A 中断后 Runtime B 能继续同一 Task |
| Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| Skill Ownership | Runtime 修改 Projection 不直接修改 Canonical Skill |
| Cross-Runtime Memory | Runtime A 形成的长期 Memory 可被 Runtime B 使用 |
| Autonomous Event Handling | 无 Chat Prompt 时 Event 仍可更新状态、创建 Task 并触发执行 |
| Capability Governance | Runtime 无法绕过 Policy / Gateway 执行高风险动作 |
| Exactly-once Side Effect | Crash / Retry 不重复执行已完成现实动作 |

## 17. 当前文档原则

当前阶段不继续展开过细模块设计。下一步先冻结：

```text
Event / World State
Task / Semantic Checkpoint
Memory Authority
Skill Authority / Projection Boundary
Capability / Provider / Protocol
Policy / Approval
SRI
Artifact
```

这些边界严格对齐后，再进入数据库 Schema、API、详细设计和实现。