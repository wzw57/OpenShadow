# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 持有连续性。**  
> 模型、Runtime 和外部生态可以替换，属于用户的长期状态、经验、能力和治理规则不应该随之消失。

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它不试图成为另一个“大而全”的 Agent，也不重做 Runtime 已经擅长的推理、规划、Skill 激活和工具编排。Shadow 负责长期持有个人 AI 的规范化资产、任务连续性和治理边界，让 Hermes、DSH、Claude、Codex 以及未来的新 Runtime 都可以作为可替换的执行核心。

## 为什么需要 OpenShadow

模型和 Agent 框架更新很快，但人的生活、项目、经验和工作方法是长期连续的。今天很多个人 AI 系统仍然把 Memory、Task、Skill、Tool 和权限锁在具体产品、Session 或 Runtime 中，因此一旦更换技术栈，就需要重新建立上下文、恢复任务、迁移工具，甚至重新教一遍“应该怎么做”。

OpenShadow 关注的是一个更长期的问题：

> **如果未来十年模型、Runtime、工具协议和交互方式不断变化，哪些东西应该一直留下来？**

我们的答案是：**属于用户、难以重新获得、并且会随着使用不断积累的规范化个人资产。**

这包括 Task、Memory、Skill、Capability、Policy、Event / World State、Artifact，以及这些对象之间的长期关系和历史。

## 核心原则

### 1. Shadow 可以依赖外部生态提供实现，但不能依赖外部生态持有规范化个人资产

Shadow 将系统分为**稳定核心层**与**可替换实现层**。

模型、Runtime、Memory Engine、Skill 执行机制、Provider、MCP 等都可以变化；但长期事实源不能因此被迫迁移。

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余功能优先复用成熟系统。**

外部格式只能作为导入、导出、适配或派生表示，不能直接成为 Shadow 的长期事实源。

### 2. Shadow 不是 Memory Engine

Memory 只是 Shadow 的一个子系统。

几个核心对象回答的是不同问题：

| 对象 | 回答的问题 | Shadow 的职责 |
| --- | --- | --- |
| **Task** | 我现在要完成什么？ | 保存目标、进度、检查点、产物和副作用状态 |
| **Memory** | 我知道什么？ | 保存可追溯、可修正的长期认知与证据关系 |
| **Skill** | 这类事情应该怎么做？ | 持有、版本化、迁移和分发可复用方法 |
| **Capability** | 系统实际上能做什么？ | 定义稳定、可治理的动作或查询契约 |
| **Policy** | 什么可以做？ | 统一权限、风险、隐私、预算和审批 |
| **Event / World State** | 发生了什么、现在是什么状态？ | 让系统脱离聊天窗口持续存在 |

即使暂时移除 Memory，Shadow 仍然必须能够：

- 保存和恢复 Task / Semantic Checkpoint；
- 在不同 Runtime 之间进行语义接力；
- 持有并同步 Skill；
- 管理 Capability、Policy、Approval 和 Execution Ledger；
- 接收 Event、维护 World State、执行 Scheduler；
- 保持 Artifact、历史和副作用状态可追溯。

如果这些能力不存在，Shadow 才真的会退化成记忆引擎。

### 3. Task 属于 Shadow，Runtime 只负责推理与执行

Runtime 可以持有临时 Session、规划状态和内部上下文，但不能成为 Task 的长期事实源。

Runtime 中断、升级或被替换时，Shadow 迁移的是可验证语义状态：目标、已知事实、决策依据、完成进度、Artifact、剩余工作和副作用状态，而不是隐藏思维链或 Runtime 私有对象。

因此：

> **Task belongs to Shadow; Runtime executes it.**

### 4. Skill 资产属于 Shadow，Skill 的具体使用交给 Runtime

Skill 和 Capability 是并列的一等对象：

```text
Task
  ↓
Skill         “怎么做”
  ↓ uses
Capability    “能做什么”
  ↓ implemented by
Provider       “由谁实现”
```

但 Shadow 不需要重做 Hermes 等 Runtime 已有的 Skill execution engine。

当前边界是：

**Shadow 负责：**

- Canonical Skill identity 与原始 Skill Source；
- Version / Provenance / Trust；
- 用户级启用、禁用与可见范围；
- Runtime compatibility；
- Runtime Projection / Sync 状态；
- 导入、导出、迁移与回滚；
- Runtime 新产生 Skill 的候选接收与规范化。

**Runtime 负责：**

- Skill discovery；
- 当前任务的 Skill activation；
- progressive disclosure；
- Skill 内部组合与编排；
- Runtime-native bundle / prompt / reference 加载；
- Runtime 内部工具使用策略。

一句话：

> **Shadow controls availability; Runtime controls activation.**

Runtime 中的 Skill 表示属于可删除、可重建的 Projection。Runtime 学到的新 Skill 只能先成为 Candidate，不能直接修改 Canonical Skill。

如果未来事实证明 Runtime 的 Skill 选择能力不足，可以增加一个**可插拔 Skill Manager**负责高级检索、关系管理和路由，但它不是稳定核心的一部分，可以独立替换升级。

### 5. Capability 是长期能力契约，MCP 只是协议

Capability 表示稳定、可治理的动作或查询语义，例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

具体由哪个 Provider、通过 MCP、REST、CLI、IPC 还是 Local API 实现，可以变化。

> **Tool 是接口，Capability 是长期能力资产，Skill 是可复用经验，MCP 是协议。**

所有现实副作用仍统一经过 Capability Gateway、Policy、Approval、Idempotency 和 Execution Ledger。Runtime 不能因为直接支持 MCP 或 Tool Calling 就绕过 Shadow 的治理。

### 6. Memory 是决策基础，不是长期 RAG

Shadow 区分：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes / Summaries / Graphs
```

原始证据负责保留事实来源，Canonical Memory 表达当前可修正、可追溯的认知；向量索引、摘要和图结构只是可重建派生层。

Memory Engine 可以替换，但不能拥有 Canonical Memory 的唯一事实源。

### 7. Shadow 围绕 Event、World State 和 Task 运行，而不是围绕聊天窗口运行

Task 可以来自用户，也可以来自 Event、Schedule 或 Condition。即使删除 Chat UI，Shadow 仍然应该能够维护 World State、恢复等待任务、选择 Runtime、执行经过治理的 Capability 并记录结果。

规则、`Pulse`、本地小模型等可以降低 7×24 运行成本，但这些属于实现策略，不是 Shadow 的核心所有权原则。

## 架构概览

```text
人 / 数字世界 / 物理世界
          │
          ▼
Interaction / Event Sources
          │
          ▼
┌──────────────────────────────────────────────┐
│                 SHADOW CORE                  │
│              稳定连续性核心层                 │
│                                              │
│ Identity / Policy       Event / World State  │
│ Task / Checkpoint       Memory Authority      │
│ Skill Authority         Runtime Registry / SRI│
│ Context Compiler        Scheduler             │
│ Capability Registry / Gateway / Ledger        │
│ Artifact / History                            │
└──────────────────────────────────────────────┘
          │
          ├─ Replaceable Runtime
          │  Hermes · DSH · Claude · Codex · Future
          │
          ├─ Replaceable Engines / Managers
          │  Memory Engine · optional Skill Manager
          │
          └─ Replaceable Providers / Protocols
             Home · PC · Server · Email · Files · Web
             MCP · REST · CLI · IPC · Local API
```

Skill 路径：

```text
Canonical Skill Store
        │
        ├─ version / provenance / trust / scope
        │
        ▼
Runtime Skill Adapter
        │
        ▼
Disposable Runtime Projection
        │
        ▼
Runtime
  discovery / activation
  disclosure / composition
  execution
        │
        ▼
usage / change events
        │
        ▼
Shadow
```

## Shadow 持有什么，外部系统做什么

| Shadow 稳定持有 / 治理 | 可替换实现 |
| --- | --- |
| Task / Semantic Checkpoint | Agent Loop / Planning |
| Raw Evidence / Canonical Memory | Memory Engine / Search Engine |
| Canonical Skill / Version / Provenance | Runtime-native Skill Engine / optional Skill Manager |
| Capability Contract / Policy / Ledger | Provider / MCP Server / Tool implementation |
| Event / World State / Scheduler | Event source adapters / notification channels |
| Runtime Registry / SRI / Binding | Hermes / DSH / Claude / Codex |
| Context Compiler | Runtime-specific prompt / context format |
| Artifact / audit history | Storage backend implementation |

## v0.1 最小可行版本

第一版只验证连续性和边界，不追求做完整个人 AI 平台。

### 核心范围

- Event / World State；
- Task / Semantic Checkpoint / Artifact；
- Raw Evidence / Canonical Memory 基础闭环；
- **Skill Store、Version / Provenance / Trust、Runtime Projection / Sync**；
- SRI、至少两个 Runtime Adapter、Context Compiler；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Execution Ledger；
- Scheduler / Event-driven execution；
- PostgreSQL + 本地优先单机部署。

V0.1 **不要求**自研 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine 或完整 Workflow Engine。优先验证 Runtime 自身能否完成 Skill 发现、选择和编排。

### 必须通过的验证

| 场景 | 验证目标 |
| --- | --- |
| Runtime 连续性 | Runtime A 中断后 Runtime B 能继续同一个 Task |
| Skill 可迁移性 | 同一 Canonical Skill 可同步/投影到两个 Runtime |
| Skill 所有权 | Runtime 修改 Projection 不会直接篡改 Canonical Skill |
| Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| 自主事件处理 | 无 Chat Prompt 时 Event 也能更新状态、创建 Task 并触发执行 |
| Capability 治理 | Runtime 不能绕过 Policy / Gateway 执行高风险动作 |
| 副作用安全 | Crash / Retry 不重复执行已完成动作 |

## 文档

当前阶段只保留前期设计文档，详细设计将在核心边界冻结后重新展开。

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

**前期设计对齐 / MVP 实现前。**

当前重点是冻结：哪些资产必须由 Shadow 长期持有，哪些能力应该交给 Runtime / Engine / Provider。只有边界稳定后，才进入数据库 Schema、API 和详细实现。