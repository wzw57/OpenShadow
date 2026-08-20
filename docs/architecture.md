# OpenShadow 概要设计

**文档状态：前期设计基线 / 待核心契约冻结**

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

当前设计刻意区分两件事：

- **逻辑架构可以完整**：把所有权、连续性、治理和替换边界想清楚；
- **物理实现必须简单**：V0.1 采用模块化单体，不把每个概念都做成独立服务。

核心工程原则：

> **Design the boundary early; build the mechanism only when needed.**

---

## 1. 宏观结构：五个逻辑域

Shadow Core 只划分为五个逻辑域：

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

这五个域是**代码与责任边界，不是五个微服务**。

V0.1 可以仍然只是：

```text
1 Shadow process
1 PostgreSQL
1 artifact directory
1 background worker
1 primary Runtime
several adapters
```

---

## 2. Task & Continuity

这一域是 Shadow 的主干，负责让长期工作脱离任何单一 Runtime Session 生存。

包含的逻辑职责：

```text
Durable Task
Task Supervisor
Semantic Checkpoint
Runtime Checkpoint Ref
Runtime Binding
Artifact refs
Handoff / Recovery
```

核心边界：

> **Shadow owns durable work; Runtime owns execution decomposition.**

Runtime 可以自由使用 Subtask、Subagent、Workflow、DAG、Planner 等内部结构，Shadow 不同步 Runtime 内部 Task Graph。只有某项内部工作需要跨 Session / Runtime 生存、长期等待、独立调度或用户独立管理时，才考虑晋升为新的 Shadow Task。

Shadow 负责监督，不负责替 Runtime 规划：

> **Shadow supervises execution; it does not plan execution.**

Supervisor 优先使用确定性逻辑处理 health、timeout、deadline、retry、waiting、checkpoint 和 completion commit。只有语义判断无法靠规则完成时，才可调用模型或 Human Approval。

Checkpoint 分两层：

- **Runtime Checkpoint**：runtime-specific、可 opaque，用于同 Runtime 高保真恢复；
- **Semantic Checkpoint**：runtime-neutral，用于 Runtime 切换、长期暂停或原生状态丢失。

> **Shadow defines durability boundaries; Runtime retains freedom over its internal state model.**

---

## 3. Memory & Personal Assets

这一域负责用户随着时间积累、需要跨 Runtime 保留的长期资产。

主要对象：

```text
Raw Evidence
Canonical Memory
Task Working Memory
Canonical Skill
Skill Source / Version / Provenance / Trust
```

### Memory

> **Memory 默认可访问，但默认不注入。**

事实层级：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

Shadow 持有 Memory truth、provenance、validity、scope 与访问边界；Mem0、LangMem、Graphiti、MemOS 等只作为可替换 Memory Intelligence。

Runtime 通过语义化 Recall Intent 请求历史信息，Shadow 再调用 Memory Engine 获取候选并治理结果。

### Skill

> **Shadow controls availability; Runtime controls activation.**

Shadow 持有 Canonical Skill、版本、来源、信任和 Runtime Projection 记录；Runtime 负责 discovery、activation、progressive disclosure、composition 与执行。

Runtime-native Skill 表示是可删除、可重建的 Projection，不是长期事实源。

---

## 4. Control & Governance

这一域负责 Shadow 的权威控制，而不是替 Runtime 思考。

逻辑职责包括：

```text
Policy
Capability
Approval
Action / Idempotency
Execution Ledger
Task supervision rules
```

基本关系：

```text
Runtime proposes action
        ↓
Shadow authorization / governance
        ↓
Provider executes
        ↓
Ledger records what happened
```

核心原则：

> **Intelligence may be outsourced; authority may not.**

LLM 可以辅助语义判断、分类、验证和解释，但不能直接修改 Shadow 的权威状态。

例如：

```text
LLM / Runtime proposes completion
            ↓
Shadow checks durable facts
            ↓
Shadow commits Task state
```

Capability 的精确边界仍需继续冻结，但 Shadow 不应退化成“所有 Runtime Tool 的统一平台”。Runtime 自己执行域内的 Planner、Subagent、临时 sandbox、纯计算等工具继续由 Runtime 自主管理；需要进入 Shadow 治理域的动作再通过统一控制路径。

---

## 5. World State & Scheduler

这一域让 Shadow 不依赖聊天窗口持续存在。

```text
External Event
     ↓
Event
     ↓
World State
     ↓
Rule / Condition / Schedule
     ↓
create / resume / inspect Task
```

主要职责：

```text
Event
World State
Scheduler
Condition
Background Jobs
```

Event 表示“发生了什么”；World State 表示“现在是什么状态”；Scheduler / Condition 决定“什么时候需要重新行动”。

V0.1 不需要 Kafka、RabbitMQ 或复杂 Event Bus。优先使用普通同步调用、PostgreSQL durable state/events 和一个 background worker；只有真实并发与扩展需求出现后再引入消息中间件。

---

## 6. Integration & Runtime Bridge

这一域保护 Shadow Core 不被任何具体 Runtime、Memory Engine、Provider 或模型实现绑定。

主要 Adapter：

```text
SRI / Runtime Adapter
Context Builder / Hydration
Memory Engine Adapter
Provider Adapter
Model Adapter
```

统一模式：

```text
Shadow Contract
      ↓
Adapter
      ↓
Replaceable Implementation
```

例如：

```text
Task → SRI → Hermes / DSH
Memory Access → Adapter → Mem0
Capability → Provider Adapter → Google / Home / Server
Semantic helper → Model Adapter → local/cloud model
```

`Model Adapter` 在 V0.1 只保持很薄，不提前建设复杂 Intelligence Gateway、多模型路由或独立 Evaluator 平台。需要语义智能的模块可以通过统一薄接口调用模型，但权威状态仍由 Shadow Core 决定。

---

## 7. 数据与一致性

V0.1 尽量使用单一权威数据库降低一致性复杂度：

```text
PostgreSQL
├─ Task / Checkpoint metadata
├─ Event / World State
├─ Memory metadata / Canonical Memory
├─ Skill metadata
├─ Policy / Approval
└─ Execution Ledger

Artifact Store / Local Files
└─ large files / reports / raw artifacts
```

Artifact 在 PostgreSQL 中保存 metadata / ref，大文件保存在本地文件系统或 NAS。

原则：

- 能在同一 PostgreSQL transaction 中完成的权威状态更新，优先放在同一事务；
- 外部 Provider 副作用通过 Ledger / idempotency / reconciliation 处理；
- 不在 V0.1 同时引入多套数据库作为事实源；
- Vector / Graph 等索引属于可重建派生实现。

---

## 8. 通信、智能与可观测性

V0.1 默认：

```text
内部模块：普通函数 / service 调用
持久状态：PostgreSQL
后台任务：单 background worker
外部实现：Adapter
```

智能使用遵循：

```text
Deterministic first
      ↓ insufficient
Model-assisted semantic judgment
      ↓ high-risk / subjective
Human approval
```

日志、错误、重试、恢复和基本 tracing 属于横切工程能力，不单独提升为一级架构域。

Secrets 也不作为一级域；实现上必须与 Runtime 隔离，Runtime 默认只获得被授权的能力，而不是长期 raw credentials。

---

## 9. V0.1 物理结构

建议代码组织：

```text
openshadow/
├─ task/          # Task & Continuity
├─ assets/        # Memory / Skill / Evidence
├─ control/       # Policy / Capability / Ledger
├─ world/         # Event / World State / Scheduler
├─ integrations/  # Runtime / Memory / Provider / Model adapters
├─ storage/
├─ api/
└─ worker/
```

它们仍然运行在一个模块化单体中。

V0.1 明确不要求：

- 微服务；
- Kubernetes；
- Kafka / RabbitMQ；
- 自研 Agent Loop / Runtime Planner；
- 同步 Runtime Subtask Graph；
- 完整 Workflow Engine；
- 自研 Memory Engine；
- 自研 Skill Resolver；
- 复杂 Intelligence Gateway；
- 多模型路由平台；
- 多数据库事实源。

---

## 10. 架构验收

V0.1 优先证明：

1. Runtime 消失后 Durable Task 和个人资产仍存在；
2. Runtime A 可以通过 Semantic Checkpoint 将长期工作交给 Runtime B；
3. Runtime 保留自己的 Planner / Subtask / Skill execution 自由；
4. Memory Engine / Runtime / Provider 可替换而不迁移 Canonical Assets；
5. Event / Scheduler 能在没有 Chat Prompt 时推进长期工作；
6. Shadow 能治理进入其权限域的动作并记录外部副作用；
7. 关闭 Memory 后 Task / Control / Event / Runtime 主干仍然有意义。

---

## 11. 当前仍需冻结

下一步继续讨论 Contract，而不是继续增加一级模块：

```text
Capability / Runtime Tool 的精确治理边界
Policy / Approval semantics
SRI / Runtime Handoff 最低保证
Event / World State consistency
Identity / Trust / Privacy
Artifact lifecycle
```

核心宏观结构保持五个逻辑域，不再因为新概念增加一级架构盒子。