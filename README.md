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

| 对象 | 回答的问题 | Shadow 的职责 |
| --- | --- | --- |
| **Task** | 我现在持续承诺完成什么？ | 持有 Durable Work、Checkpoint、Artifact 与副作用状态 |
| **Memory** | 我知道什么？ | 保存可追溯、可修正的长期认知与证据关系 |
| **Skill** | 这类事情应该怎么做？ | 持有、版本化、迁移和分发可复用方法 |
| **Capability** | 系统实际上能做什么？ | 定义稳定、可治理的动作或查询契约 |
| **Policy** | 什么可以做？ | 统一权限、风险、隐私、预算和审批 |
| **Event / World State** | 发生了什么、现在是什么状态？ | 让系统脱离聊天窗口持续存在 |

即使暂时移除 Memory，Shadow 仍然必须能够保存和恢复 Task、监督和调度长期执行、跨 Runtime 接力、同步 Skill、治理 Capability / Policy / Ledger、维护 Event / World State / Scheduler，并保持 Artifact 和副作用状态可追溯。

### 3. Shadow 持有长期工作连续性，Runtime 自由决定如何执行

Shadow Task 是需要跨 Runtime / Session 持续存在的 **Durable Work**，不是 Runtime 内部 Planner 的 Task Node。

> **Shadow owns durable work; Runtime owns execution decomposition.**

Runtime 可以自由拆 Subtask、调用 Subagent、建立 Workflow 或使用任意 Planner；这些内部结构默认属于 Runtime，不要求映射为 Shadow Task。只有某项内部工作需要跨 Session / Runtime 生存、长期等待、独立调度、独立 Policy / Budget 或用户独立管理时，才考虑晋升为新的 Shadow Task。

Shadow 作为上层控制面负责监督而不是规划：

> **Shadow supervises execution; it does not plan execution.**

Task Supervisor 优先使用确定性检查处理 Runtime health、timeout、deadline、retry、schedule、Artifact、Approval、Ledger 和 side-effect state。只有确定性规则不足时才调用可替换 Semantic Verifier，高风险场景再进入 Human Approval。

Runtime 可以提出 progress / completion，但 Durable Task 的最终状态由 Shadow 提交：

> **Runtime proposes progress and completion; Shadow commits durable task state.**

Checkpoint 分为两层：Runtime Checkpoint 可以是 opaque 的原生 Session / Planner State 引用，用于同一 Runtime 高保真恢复；Semantic Checkpoint 是 runtime-neutral 的恢复语义，用于切换 Runtime、长期暂停或原 Runtime 状态丢失。

> **Shadow defines durability boundaries; Runtime retains freedom over its internal state model.**

因此 Shadow 不要求迁移隐藏思维链、KV Cache 或 Runtime 私有 Planner Graph，也不规定 Runtime 每执行多少步必须 Checkpoint。

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

Shadow 负责 Canonical Skill、Raw Source、Version / Provenance / Trust、Scope、Runtime compatibility、Projection / Sync、导入导出和迁移；Runtime 负责 discovery、activation、progressive disclosure、composition 和执行。

> **Shadow controls availability; Runtime controls activation.**

Runtime Skill 表示是可删除、可重建的 Projection。Runtime 新学到或修改的 Skill 只能先成为 Candidate，不能直接修改 Canonical Skill。

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

所有现实副作用统一经过 Capability Gateway、Policy、Approval、Idempotency 和 Execution Ledger。

### 6. Memory 默认可访问，但默认不注入

Shadow 区分：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes / Summaries / Graphs
```

长期拥有大量 Memory 不意味着每个 Task 都做 Recall。Runtime 只在当前问题可能依赖历史信息时主动提出 Recall Intent；Shadow 控制 Scope、Privacy、Validity 和 Context Budget，再通过可替换 Memory Engine 获取候选。

> **Shadow 持有 Memory truth 与访问边界；外部 Memory Engine 提供提取、检索、整理和关联智能。**

当前默认实现方向：

- **Shadow + PostgreSQL**：Raw Evidence / Canonical Memory / Task Working Memory 的事实源；
- **Mem0 OSS**：第一版在线 Recall / candidate retrieval；
- **LangMem**：后台 extraction / consolidation Candidate；
- **Graphiti**：第二阶段 Derived Memory Graph / multi-hop association 实验；
- **MemOS**：后续作为替代 Memory Engine 评估。

这些组件都通过 Adapter 接入，可以替换；派生索引、摘要和图可以重建。

Memory 的目标不是 Recall 越多越好，而是：

> **在尽量少占用 Runtime 注意力的前提下，自动提供足以改善当前决策的最少相关 Memory。**

### 7. Shadow 围绕 Event、World State 和 Task 运行，而不是围绕聊天窗口运行

Task 可以来自用户，也可以来自 Event、Schedule 或 Condition。即使删除 Chat UI，Shadow 仍然应该能够维护 World State、监督和恢复等待任务、选择 Runtime、执行经过治理的 Capability 并记录结果。

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
│ Durable Task / Supervisor / Checkpoint       │
│ Memory Authority        Skill Authority      │
│ Runtime Registry / SRI  Context Compiler     │
│ Scheduler               Capability Gateway   │
│ Execution Ledger        Artifact / History   │
└──────────────────────────────────────────────┘
          │
          ├─ Replaceable Runtime
          │  Hermes · DSH · Claude · Codex · Future
          │
          ├─ Replaceable Engines / Managers
          │  Mem0 · LangMem · Graphiti · Future
          │  optional Verifier / Memory / Skill Manager
          │
          └─ Replaceable Providers / Protocols
             Home · PC · Server · Email · Files · Web
             MCP · REST · CLI · IPC · Local API
```

## Shadow 持有什么，外部系统做什么

| Shadow 稳定持有 / 治理 | 可替换实现 |
| --- | --- |
| Durable Task / Supervisor / Semantic Checkpoint | Runtime Planner / Subtask / Workflow |
| Runtime Checkpoint Reference / Binding | Runtime-native Session / Checkpoint implementation |
| Raw Evidence / Canonical Memory / Task Working Memory | Mem0 / LangMem / Graphiti / Search Engine |
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
- Durable Task / Task Supervisor；
- Runtime Checkpoint Reference / Semantic Checkpoint / Artifact；
- deterministic-first Task supervision；
- Raw Evidence / Canonical Memory / Task Working Memory；
- Memory Access API + Mem0 Adapter；
- LangMem 后台 Memory Candidate / Consolidation 基础实验；
- Skill Store、Version / Provenance / Trust、Runtime Projection / Sync；
- SRI、至少两个 Runtime Adapter、Context Compiler；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Execution Ledger；
- Scheduler / Event-driven execution；
- PostgreSQL + 本地优先单机部署。

V0.1 **不要求**自研 Runtime Planner、同步 Runtime Subtask Graph、自研 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine、Learned Memory Router 或完整 Workflow Engine。Graphiti 关联图和 Semantic Verifier 先作为后续实验，不进入默认主链。

### 必须通过的验证

| 场景 | 验证目标 |
| --- | --- |
| Durable Task Ownership | Runtime 内部 Planner / Subtask 不进入 Shadow，Durable Task 仍独立存在 |
| Task Supervision | Shadow 可用确定性检查完成 wait / retry / resume / checkpoint / completion commit |
| Runtime 连续性 | Runtime A 中断后 Runtime B 能从 Semantic Checkpoint + durable state 继续 Task |
| Runtime-native Resume | 原 Runtime 可通过 opaque Runtime Checkpoint / Session Ref 高保真恢复 |
| Completion Ownership | Runtime propose completion，Shadow commit Durable Task 状态 |
| Skill 可迁移性 | 同一 Canonical Skill 可同步/投影到两个 Runtime |
| Skill 所有权 | Runtime 修改 Projection 不会直接篡改 Canonical Skill |
| Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| Memory Selectivity | 简单 Task 可不 Recall，需要历史时只注入少量相关 Memory |
| Memory Engine 可替换 | 更换在线检索 Engine 不迁移 Canonical Memory |
| 自主事件处理 | 无 Chat Prompt 时 Event / Scheduler / Supervisor 可推进 Task |
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

当前重点是冻结：哪些资产必须由 Shadow 长期持有，哪些控制能力属于 Shadow，哪些执行能力应该交给 Runtime / Engine / Provider。只有边界稳定后，才进入数据库 Schema、API 和详细实现。