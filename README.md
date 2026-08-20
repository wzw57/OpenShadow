# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 持有连续性。**  
> 模型、Runtime 和外部生态可以替换，属于用户的长期状态、经验、能力和治理规则不应该随之消失。

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它不试图成为另一个“大而全”的 Agent，也不重做 Runtime 已经擅长的推理、规划、Skill 激活和工具编排。Shadow 负责长期持有规范化个人资产、任务连续性和治理边界，让 Hermes、DSH、Claude、Codex 以及未来的新 Runtime 都可以作为可替换的执行核心。

## 核心原则

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余功能优先复用成熟系统。**

> **Shadow owns durable work; Runtime owns execution decomposition.**

> **Shadow supervises execution; it does not plan execution.**

> **Shadow controls availability; Runtime controls Skill activation.**

> **Memory 默认可访问，但默认不注入。**

> **Intelligence may be outsourced; authority may not.**

也就是说：Runtime 可以越来越聪明，但不能成为用户长期状态、权限和任务连续性的唯一事实源。

## 五个逻辑域

OpenShadow 的宏观架构只保留五个一级逻辑域：

```text
                 User / Apps / Event Sources
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│                    SHADOW CORE                      │
│                                                     │
│  1. Task & Continuity                              │
│  2. Memory & Personal Assets                       │
│  3. Control & Governance                           │
│  4. World State & Scheduler                        │
│  5. Integration & Runtime Bridge                   │
└───────────────────────┬─────────────────────────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
       Runtime        Engines       Providers
     Hermes / DSH   Mem0/LangMem   Gmail/GitHub
     Claude/Codex   Graphiti/...   Home/Server/...
```

这五个域是**责任与代码边界，不是五个微服务**。

### 1. Task & Continuity

负责长期工作的连续性：

```text
Durable Task
Task Supervisor
Semantic Checkpoint
Runtime Checkpoint Ref
Runtime Binding
Handoff / Recovery
```

Runtime 内部的 Subtask、Subagent、Workflow 和 Planner 默认属于 Runtime；Shadow 不同步它们。

### 2. Memory & Personal Assets

负责用户长期积累的资产：

```text
Raw Evidence
Canonical Memory
Task Working Memory
Canonical Skill
Version / Provenance / Trust
```

Memory Engine 和 Runtime Skill Engine 都可以替换，但 Canonical Assets 不随它们迁移。

### 3. Control & Governance

负责 Shadow 的权威控制：

```text
Policy
Capability
Approval
Idempotency
Execution Ledger
```

LLM 可以辅助语义判断，但不能直接提交 Shadow 的权威状态。

### 4. World State & Scheduler

负责持续运行：

```text
Event
World State
Scheduler
Condition
Background Jobs
```

即使没有 Chat Prompt，Shadow 也可以根据事件、时间和条件恢复或创建 Task。

### 5. Integration & Runtime Bridge

负责所有可替换实现的边界：

```text
SRI / Runtime Adapter
Memory Engine Adapter
Provider Adapter
Model Adapter
Context / Hydration
```

统一模式：

```text
Shadow Contract
      ↓
Adapter
      ↓
Replaceable Implementation
```

## Task 边界

Shadow Task 是需要跨 Runtime / Session 生存的 **Durable Work**，不是 Runtime 内部 Planner Task。

Runtime 可以自由拆 Subtask、调用 Subagent、建立 Workflow。只有内部工作跨过持久化边界，例如需要长期等待、独立调度、跨 Runtime 生存或用户独立管理时，才考虑晋升为新的 Shadow Task。

Checkpoint 分两层：

- **Runtime Checkpoint**：runtime-specific、可 opaque，用于同 Runtime 高保真恢复；
- **Semantic Checkpoint**：runtime-neutral，用于切换 Runtime、长期暂停或 Runtime 原生状态丢失。

Runtime 可以提出 progress / completion，但 Durable Task 的最终状态由 Shadow 提交。

## Memory 与 Skill 边界

Memory：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Index / Summary / Graph
```

Shadow 持有 Memory truth 与访问边界；Mem0、LangMem、Graphiti、MemOS 等提供可替换的 Memory Intelligence。

Skill：

```text
Raw Skill Source
      ↓
Canonical Skill
      ↓
Runtime Projection
      ↓
Runtime-native execution
```

Shadow 控制 Skill availability，Runtime 控制 discovery / activation / composition / execution。

## 轻量实现原则

OpenShadow 的复杂度应该主要存在于**语义边界**，而不是运行时拓扑。

V0.1 推荐物理结构：

```text
1 Shadow process
1 PostgreSQL
1 artifact directory
1 background worker
1 primary Runtime
several adapters
```

默认内部通信使用普通函数 / service 调用；持久状态使用 PostgreSQL；后台工作使用单 worker。V0.1 不需要 Kafka、RabbitMQ、Kubernetes 或复杂微服务。

代码组织可以是：

```text
openshadow/
├─ task/
├─ assets/
├─ control/
├─ world/
├─ integrations/
├─ storage/
├─ api/
└─ worker/
```

## v0.1 要证明什么

第一版不追求完整个人 AI 平台，只证明几个核心命题：

1. Runtime 消失后 Durable Task 和个人资产仍存在；
2. Runtime A 可以通过 Semantic Checkpoint 将长期工作交给 Runtime B；
3. Runtime 保留自己的 Planner / Subtask / Skill execution 自由；
4. Memory Engine / Runtime / Provider 可替换而不迁移 Canonical Assets；
5. Event / Scheduler 能在没有 Chat Prompt 时推进长期工作；
6. Shadow 能治理进入其权限域的动作并记录外部副作用；
7. 关闭 Memory 后 Task / Control / Event / Runtime 主干仍然有意义。

V0.1 明确不做：自研 Agent Loop、同步 Runtime Subtask Graph、完整 Workflow Engine、自研 Skill Resolver、复杂 Intelligence Gateway、多模型路由平台、微服务化和多数据库事实源。

## 文档

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

**前期设计对齐 / MVP 实现前。**

当前重点是继续冻结少量关键 Contract，而不是继续增加一级模块。