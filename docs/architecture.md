# OpenShadow 概要设计

**文档状态：前期设计基线 / 待核心契约冻结**

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它不负责成为最聪明的 Agent，也不重做 Runtime 已经具备的推理、规划、Skill 激活和工具编排。Shadow 的职责是长期持有规范化个人资产、维护 Task 连续性、统一治理现实能力，并把这些资产安全地交给可替换 Runtime 使用。

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

---

## 1. 最底层设计原则

### 1.1 外部实现可以依赖，规范化个人资产不能外包所有权

> **Shadow 可以依赖外部生态提供实现，但不能依赖外部生态持有规范化个人资产。**

因此系统分为：

- **稳定核心层**：长期事实源、治理、连续性和迁移边界；
- **可替换实现层**：Runtime、Memory Engine、Skill 执行机制、Provider、协议和模型。

外部格式可以作为 Import / Export / Adapter / Projection，但不能直接成为 Shadow 的唯一长期事实源。

### 1.2 判断某功能是否进入核心

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余功能优先复用成熟系统。**

### 1.3 Shadow 不等于 Memory Engine

Memory 是 Shadow 的一个子系统，不是 Shadow 的全部。

即使暂时关闭 Memory 子系统，Shadow 仍然必须能够：

- 保存与恢复 Task / Semantic Checkpoint；
- 在多个 Runtime 之间接力 Task；
- 持有并同步 Canonical Skill；
- 管理 Capability / Policy / Approval / Execution Ledger；
- 接收 Event、维护 World State、运行 Scheduler；
- 保存 Artifact、历史和副作用状态。

这条作为架构自检：**如果移除 Memory 后系统只剩空壳，说明 Shadow 的边界设计错了。**

---

## 2. 稳定核心层

Shadow 当前确认长期持有或治理：

- Identity / Policy；
- Event / World State；
- Task / Semantic Checkpoint；
- Raw Evidence / Canonical Memory；
- Canonical Skill / Version / Provenance / Trust；
- Capability Contract / Registry；
- Runtime Registry / SRI / Binding；
- Context Compiler；
- Capability Gateway / Execution Ledger；
- authoritative Scheduler；
- Artifact / History；
- Runtime、Memory、Skill、Provider 的迁移与升级元数据。

优先交给外部实现：

- Agent Loop / Planning；
- Runtime-native Skill discovery / activation / progressive disclosure / composition；
- Hermes、DSH、Claude、Codex 等 Runtime；
- Mem0、LangMem、Graphiti、MemOS 等 Memory Intelligence 实现；
- Browser Agent / Coding Agent / Research Agent；
- Home Assistant / Server Agent / Email / Calendar Provider；
- MCP / REST / CLI / IPC 等协议；
- Embedding / Vector DB / Graph DB / LLM Serving。

V0.1 采用**模块化单体 + PostgreSQL**，不因为逻辑边界而提前拆微服务。

---

## 3. 核心对象模型

| 对象 | 核心语义 | Shadow 为什么持有 |
| --- | --- | --- |
| **Identity** | 用户身份、长期偏好、信任与隐私基线 | 所有 Runtime 的共同根身份 |
| **Event** | 已发生事实的持久记录 | 支撑审计、重建和状态投影 |
| **World State** | 当前世界状态的紧凑投影 | 让系统持续面对“现在” |
| **Task** | 需要持续完成的工作及其状态 | 不能随 Runtime Session 消失 |
| **Memory** | 对历史证据形成的可追溯认知 | 属于用户，而非某个 Agent |
| **Skill** | 可复用的方法、经验和程序性知识 | 用户教会 AI 的“怎么做”应可迁移 |
| **Capability** | 稳定、可治理的动作或查询契约 | 表示用户真正拥有的可执行能力 |
| **Policy** | 权限、风险、隐私、预算和审批规则 | 必须跨 Runtime 统一执行 |
| **Artifact** | 文件、日志、报告、工具结果 | 支撑长期 Task 与跨 Runtime 接力 |
| **Runtime Binding** | 当前执行器和临时 Session 引用 | 只绑定执行，不拥有 Task |

对象关系可以用五个问题理解：

```text
Task        = 我现在要完成什么
Memory      = 我知道什么
Skill       = 这类事情应该怎么做
Capability  = 系统实际上能做什么
Policy      = 哪些行为被允许
```

---

## 4. Task 与 Runtime 连续性

### 4.1 Task 属于 Shadow

Runtime 只负责推理和执行。Hermes Session、DSH Session、Claude Thread 等都只是临时执行引用。

Task 至少长期保留：

```text
Goal
Current Stage
Known Facts
Decisions / Evidence
Completed Work
Artifacts / Tool Results
Remaining Work
Policy / Budget
Runtime Binding
Checkpoint
Side-effect State
```

### 4.2 Semantic Checkpoint

跨 Runtime 接力迁移的是可验证语义状态，而不是 hidden chain-of-thought、KV Cache、Runtime 私有 Planner Graph 或 Runtime-specific Session object。

因此“连续”意味着：**目标、进度、证据、产物、剩余工作和副作用状态不丢失。**

### 4.3 SRI

SRI（Shadow Runtime Interface）提供稳定 Runtime 边界，概要能力包括：

```text
execute
resume
pause
cancel
checkpoint
status
capabilities
health
```

Runtime Adapter 可以被独立替换和升级。

---

## 5. Skill 边界

### 5.1 Skill 与 Capability

Skill 与 Capability 是并列的一等对象，但执行时 Skill 通常使用 Capability：

```text
Task
  ↓
Skill         “怎么做”
  ↓ uses
Capability    “能做什么”
  ↓ implemented by
Provider       “由谁实现”
```

Skill 描述方法，不授予权限。

### 5.2 Shadow 持有什么

Shadow 的 Skill Authority 只负责连续性和资产所有权：

- Canonical Skill identity；
- Raw Skill Source；
- Version / Provenance / Trust；
- 用户级 Enable / Disable / Scope；
- Runtime compatibility；
- Projection / Sync records；
- Import / Export / Migration / Rollback；
- Runtime-created / modified Skill Candidate 的接收与规范化。

### 5.3 Runtime 持有什么

Runtime 负责单次执行中的 Skill 使用策略：

- Skill discovery；
- Skill activation；
- progressive disclosure；
- Skill composition / orchestration；
- runtime-native bundle / prompt / reference loading；
- Runtime 内部工具使用策略。

核心边界：

> **Shadow controls availability; Runtime controls activation.**

### 5.4 Runtime Projection 是派生资产

```text
Raw Skill Source
      ↓ import / normalize
Canonical Skill
      ↓ Runtime Skill Adapter
Runtime Projection
      ↓
Runtime
```

Runtime Projection 可以删除、重新生成和覆盖，不是长期事实源。Runtime 新建或修改 Skill 时，只能形成 Candidate / Change Event，再由 Shadow 决定是否规范化进入 Canonical Skill。

### 5.5 可插拔 Skill Manager

V0.1 不把 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine 写进稳定核心。

如果后续真实使用证明 Runtime 的 Skill 选择能力不足，可以增加独立的 **Skill Manager**。它可以负责高级检索、关系管理、冲突处理或路由，但必须：

- 不拥有 Canonical Skill 唯一事实源；
- 可以被整体替换；
- 升级失败不破坏 Skill 资产；
- 不绕过 Runtime 和 Capability 的既有边界。

---

## 6. Memory 边界

### 6.1 基本原则

> **Memory 默认可访问，但默认不注入。**

Shadow 的 Memory 核心不是“每次 Task 都做 RAG”，而是让 Runtime 在真正需要历史信息时能够自动 Recall，并且只获得足以改善当前决策的少量相关 Memory。

Memory 采用三层事实模型：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- **Raw Evidence**：事实来源；
- **Canonical Memory**：当前可修正、可追溯、带时间有效性的长期认知；
- **Derived Layer**：embedding、FTS、摘要、聚类、知识图、关系边等，可以删除重建。

Memory Engine 不得拥有 Canonical Memory 的唯一事实源。

### 6.2 Shadow 与 Memory Engine 的职责边界

> **Shadow 持有 Memory truth、访问边界和 Task continuity；外部 Memory Engine 提供提取、检索、整理、关联等智能。**

Shadow 负责：

- Raw Evidence / Canonical Memory；
- Scope / Privacy / Trust / Provenance；
- Current / Superseded / Temporal Validity；
- Memory Access API；
- 外部候选结果的治理与过滤；
- Task Working Memory；
- Background Job / Scheduler；
- Memory Engine Adapter 生命周期。

外部 Engine 可以负责：

- extraction；
- semantic / lexical / entity retrieval；
- reranking；
- consolidation suggestion；
- entity linking；
- temporal / relation graph；
- multi-hop association；
- learned recall routing。

### 6.3 Runtime 与 Recall

Runtime 不应直接操作 Mem0、Graphiti 等底层实现，而是通过 Shadow Memory Access API 表达语义化 Recall Intent：

```text
Runtime / Task
      ↓
Recall Intent
“需要这个项目过去的关键架构决策”
      ↓
Shadow Memory Access API
      ↓ scope / privacy / budget
Memory Engine Adapter
      ↓
Candidate Memories
      ↓
Shadow Governance
      ↓
Task Working Memory / Runtime Context
```

Runtime 表达“需要什么”；底层 Engine 决定“怎么搜”。

### 6.4 Memory Attention

真正困难的问题不是存储，而是：

```text
什么时候应该回忆？
        ↓
应该回忆什么？
        ↓
应该回忆到多深？
```

V0.1 先使用 **Runtime 主动工具调用 + 简单 Shadow 规则**。未来可以通过稳定接口替换为 LLM Router 或 Learned Personal Memory Router。

### 6.5 Scoped / Hierarchical / Multi-index Recall

长期 Memory 需要支持：

- Global / Project / Task / Entity / Relationship / Episode Scope；
- Semantic / Entity / Temporal / Project / Type / Relation / Provenance / Lexical 等多维索引；
- NONE → LIGHT → NORMAL → DEEP → EVIDENCE 的逐级 Recall；
- Current / Superseded / historical memory validity；
- Topic / Project Summary 到具体 Memory，再到 Raw Evidence 的逐层下钻。

Vector similarity 只是候选信号之一。

### 6.6 Task Working Memory

已证明对当前 Task 有用的 Memory 进入 Shadow 持有的 Task Working Memory：

```text
Long-term Memory
      ↓ recall
Task Working Memory
      ↓
Runtime Context
```

这样长任务无需每一步重复访问长期 Memory，而且更换 Runtime 时这些已确认上下文仍随 Task 保留。

### 6.7 后台联想与 Derived Memory Graph

系统允许在空闲或低优先级阶段对新增 Event / Memory 做后台整理：

```text
New Events / Memories
        ↓
Background Association / Consolidation
        ├─ extraction / merge suggestion
        ├─ entity linking
        ├─ temporal relation
        ├─ conflict detection
        ├─ topic / cluster discovery
        └─ project / entity summary rebuild
        ↓
Candidate Updates + Derived Memory Graph
```

自动发现的 Graph Edge / Cluster / Summary 默认属于 **Derived Intelligence**，不是 Canonical Truth。低置信度联想不得静默覆盖 Canonical Memory。

### 6.8 当前默认组件分工

当前默认实现组合：

| 层 | 默认组件 | 责任 |
| --- | --- | --- |
| Memory Authority | **Shadow + PostgreSQL** | Canonical Memory、Raw Evidence、Scope、Validity、Provenance |
| Online Recall | **Mem0 OSS** | 候选检索、语义/词法/实体相关召回、reranking |
| Background Consolidation | **LangMem** | extraction、consolidation、update Candidate / Suggestion |
| Association Graph | **Graphiti（第二阶段）** | Entity / Relation / Temporal Graph、multi-hop association |
| Memory Attention | **Runtime + 简单规则起步** | 是否 Recall、Recall 意图；策略后续可替换 |
| Task Working Memory | **Shadow** | 当前 Task 已确认有用的 Memory |
| Advanced Engine | **MemOS（后续评估）** | 作为替代 Memory Engine 做实验，不成为事实源 |

这些都是 Adapter 后面的默认实现，不属于不可替换的核心 Contract。

### 6.9 设计目标

> **在尽量少占用 Runtime 注意力的前提下，自动提供足以改善当前决策的最少相关 Memory。**

未来关注的不是单纯 Recall@K，而是 irrelevant memory rate、token overhead、stale memory rate、user correction、task outcome、deep recall recovery、memory utility density 和 association / multi-hop recall 增益。

---

## 7. Capability、Provider 与协议

Capability 是稳定动作 / 查询契约，例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

Provider 是具体实现者；MCP、REST、CLI、IPC、Local API 是协议或接入方式。

> **Tool 是接口；Capability 是长期能力资产；Skill 是可复用经验；MCP 是协议。**

所有现实副作用统一经过：

```text
Runtime proposes
      ↓
Capability Gateway
      ↓
Identity / Schema
      ↓
Policy / Risk
      ↓
Approval when needed
      ↓
Idempotency
      ↓
Provider
      ↓
Execution Ledger / Audit
```

Runtime 不能因为原生支持 MCP 或 Tool Calling 就绕过 Gateway。

---

## 8. Event、World State 与 Scheduler

Shadow 不围绕聊天 Session 运行，而围绕长期状态运行：

```text
Email / Calendar / Home / Server / Files / User
                    ↓
                  Event
                    ↓
              Event Store
                    ↓
             World State
                    ↓
            Rule / Scheduler
                    ↓
          Update / Notify / Task
```

- Event = 发生了什么；
- World State = 现在是什么状态；
- Scheduler = 什么时候需要恢复或检查；
- Task = 哪件工作需要持续到完成。

`Pulse`、小模型、规则分层等属于运行成本优化，可以替换，不进入最底层所有权原则。

---

## 9. Context Compiler

Context Compiler 将 Shadow 规范化资产编译为当前 Runtime 能消费的输入。

输入可能包括：

```text
Task / Checkpoint
Relevant Memory / Task Working Memory
Available Skill references / projections
World State
Policy / Trust Profile
Allowed Capabilities
Artifact / Evidence references
```

这里的原则不是 Shadow 重新控制 Runtime 内部推理，而是确保 Runtime 切换时可以从稳定状态重新 hydrate。

---

## 10. 可替换与升级

Shadow 的长期目标不是“支持很多插件”，而是让外围技术真正可替换。

```text
Canonical Asset / Contract
          ↓
      Adapter Boundary
          ↓
Replaceable Implementation
```

适用对象包括：Runtime、Memory Engine、Memory Attention、Background Memory Worker、Skill Manager、Runtime Skill Adapter、Provider、Protocol Adapter、Search / Index Engine。

升级原则：

> **新技术主要替换 Adapter、Manager 或派生表示，不迁移规范化个人资产。**

---

## 11. V0.1 架构范围

V0.1 只证明核心边界成立：

1. Event / World State；
2. Task / Semantic Checkpoint / Artifact；
3. Raw Evidence / Canonical Memory / Task Working Memory；
4. Memory Access API + Mem0 Adapter；
5. LangMem 后台 Candidate / Consolidation 基础实验；
6. Skill Store + Version / Provenance / Trust + Runtime Projection / Sync；
7. SRI + 两个 Runtime Adapter；
8. Context Compiler；
9. Capability Registry / Gateway / Provider Binding；
10. Policy / Approval / Idempotency / Execution Ledger；
11. Scheduler / Event-driven execution；
12. PostgreSQL 本地持久化。

Graphiti Derived Memory Graph、Learned Memory Router 和 MemOS 替代后端属于后续实验。

明确不要求：自研 Agent Loop、自研 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine、完整 Workflow Engine、自研 Browser / Coding Agent、自研 Vector / Graph DB、完整 Chat / Voice 平台。

---

## 12. 架构验收

| 验收 | 目标 |
| --- | --- |
| Runtime Continuity | Runtime A 失败后 Runtime B 继续同一 Task |
| Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| Skill Ownership | Runtime 修改 Projection 不直接修改 Canonical Skill |
| Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| Memory Selectivity | 简单 Task 可不 Recall，需要历史时只提供少量相关 Memory |
| Memory Engine Replaceability | 更换 Engine 不迁移 Raw Evidence / Canonical Memory |
| Autonomous Operation | 无 Chat Prompt 时 Event / Scheduler 仍可触发 Task |
| Capability Governance | Runtime 无法绕过 Policy / Gateway 执行高风险动作 |
| Exactly-once Side Effect | Crash / Retry 不重复执行已完成动作 |

---

## 13. 当前待冻结边界

在进入 Schema 和 API 设计之前，当前仍需继续严格讨论：

```text
Task / Semantic Checkpoint 的最小语义与状态机
Memory Attention / Recall Intent 的最小 Contract
Canonical Memory 的写入 / 修正 / 冲突规则
Capability / Provider / Policy / Approval 的边界
SRI / Runtime Handoff 的最低保证
Context Compiler 的输入输出责任
Event / World State 的一致性与投影规则
Identity / Trust / Privacy 边界
Artifact 生命周期与引用语义
Scheduler / Condition / Autonomous Trigger 的权威语义
```

这些边界冻结后，再进入 PostgreSQL Schema、API 和详细实现。