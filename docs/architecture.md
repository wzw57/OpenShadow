# OpenShadow 概要设计

**文档状态：前期设计基线 / 待核心契约冻结**

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。它不负责成为最聪明的智能体，而负责持有那些必须跨模型、跨运行时、跨设备、跨会话和跨时间持续存在的个人资产，并为可替换的智能系统提供统一上下文、技能、能力与治理边界。

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

---

## 1. 设计目标

OpenShadow 解决的核心问题不是“如何再造一个 Agent”，而是如何让个人 AI 在快速变化的技术环境中保持长期连续。

系统需要满足以下目标：

1. **用户长期资产独立于 Runtime。** 更换模型或智能体时，不迁移整套个人状态。
2. **任务可以跨 Runtime 接力。** 连续性以可验证的语义状态为边界，而不是以某个 Session 为边界。
3. **Memory、Skill、Capability 都可以长期积累。** 用户不应反复教同一套偏好、方法和工具能力。
4. **所有现实动作统一治理。** Runtime 不能绕过权限、审批、幂等和执行台账直接操作外部世界。
5. **系统不依赖聊天窗口才能存在。** Event、World State、Scheduler 和 Task 使 Shadow 可以持续运行。
6. **外围技术可以持续替换。** Runtime、Memory Engine、Provider、Tool Protocol 等都应通过稳定边界接入。

---

## 2. 系统边界：稳定核心层与可替换外围

判断某个功能是否应该由 Shadow 持有的基本原则是：

> **如果它必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致，就应该进入 Shadow 的稳定核心层；否则优先复用外部成熟系统。**

### 2.1 Shadow 稳定核心层

Shadow 负责长期持有或治理：

- Identity / Policy；
- Event / World State；
- Task / Semantic Checkpoint；
- Raw Evidence / Canonical Memory；
- Skill Registry / Skill Graph / Skill Version；
- Capability Registry / Capability Contract；
- Runtime Registry / SRI；
- Context Compiler；
- Capability Gateway / Execution Ledger；
- authoritative Scheduler；
- Artifact 引用与任务产物；
- Runtime、Skill、Provider 的升级与迁移元数据。

### 2.2 可替换外围

优先复用：

- Agent Loop / Planning；
- Hermes、DSH、Claude、Codex 等 Runtime；
- Mem0、LangMem、Graphiti 等 Memory Engine；
- Browser Agent、Coding Agent、Research Agent；
- Home Assistant、Server Agent、Email / Calendar Provider；
- MCP、REST、CLI、IPC 等工具或集成协议；
- STT / TTS / 消息平台；
- Embedding、Vector DB、Graph DB、LLM Serving。

逻辑模块化不意味着微服务化。V0.1 仍以**模块化单体 + PostgreSQL**为主。

---

## 3. 核心对象模型

OpenShadow 当前确认的一等对象如下：

| 对象 | 定义 | 为什么由 Shadow 持有 |
| --- | --- | --- |
| **Identity** | 用户身份、长期偏好与信任基线 | 所有 Runtime 的共同根身份 |
| **Event** | 已经发生的事实记录 | 支撑审计、重建和状态投影 |
| **World State** | 当前世界状态的紧凑投影 | 让系统面对“现在是什么状态” |
| **Task** | 当前或长期需要完成的工作 | 不能随 Runtime Session 消失 |
| **Memory** | 对历史证据形成的可追溯认知 | 属于用户，而非某个 Agent |
| **Skill** | 可复用的方法、经验与解决策略 | 用户长期教会 AI 的“怎么做”应可迁移 |
| **Capability** | 稳定、可治理的动作或查询契约 | 表示用户真正拥有的可执行能力 |
| **Policy** | 权限、风险、隐私、预算与审批规则 | 必须跨 Runtime 统一执行 |
| **Artifact** | 文件、日志、报告、工具结果等任务产物 | 支撑长期任务与跨 Runtime 接力 |
| **Runtime Binding** | 当前执行器与临时 Session 引用 | 只记录执行绑定，不拥有 Task |

几个核心对象可以用四个问题理解：

```text
Memory      → 我知道什么？
Skill       → 这类事情应该怎么做？
Capability  → 我实际上能做什么？
Task        → 我现在要完成什么？
```

Policy 负责回答“允许做到什么程度”。

---

## 4. Task 与 Runtime

### 4.1 Task 属于 Shadow

Runtime 只负责执行 Task。Hermes Session、DSH Session、Claude Thread 等都只是临时执行引用。

Task 至少要长期保留：

- Goal；
- 当前阶段；
- 已完成工作；
- 已知事实；
- 决策与证据；
- Memory / Skill 引用；
- Artifact / Tool Result；
- 剩余工作；
- 权限与预算；
- Runtime Binding；
- 最近持久化 Checkpoint；
- 已执行副作用状态。

### 4.2 Semantic Checkpoint

Runtime 切换不追求迁移隐藏思维链、KV Cache 或 Runtime 私有 Planner 对象。

Shadow 迁移的是可验证语义状态：

```text
Task Goal
+ Current Stage
+ Known Facts
+ Decisions / Evidence
+ Completed Work
+ Artifacts / Tool Results
+ Remaining Work
+ Side-effect State
```

因此“无损接力”的含义是：**任务语义、证据、产物和副作用状态不丢失**，而不是 token-level 状态完全一致。

### 4.3 SRI

SRI（Shadow Runtime Interface）是 Shadow 与 Runtime 之间的稳定接口边界。

概要能力包括：

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

具体传输方式可以是 HTTP、JSON-RPC、Subprocess IPC 或其他 Adapter，不进入核心语义。

---

## 5. Memory

Shadow Memory 的目标不是最大化历史召回，而是**改善当前 Task 的决策质量**。

### 5.1 三层结构

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- **Raw Evidence**：事实来源，尽量保留原始证据与 provenance；
- **Canonical Memory**：当前可修正、带时间有效性的结构化认知；
- **Derived Layer**：embedding、向量索引、全文索引、图、摘要等，可删除重建。

### 5.2 Recall

Runtime 不应该默认收到“向量相似度最高的若干历史”。

Shadow 根据 Task / Step 形成 `MemoryNeed`，再由 Memory Broker 组合结构化、时间、实体、全文和语义检索，最终输出紧凑 `MemoryBundle`。

如果 Canonical Memory 不足，可以执行 Deep Recall，回到 Raw Evidence、历史 Task 和 Artifact 中查证。

---

## 6. Skill

Skill 是 OpenShadow 新增确认的一等长期资产。

> **Capability 回答“能做什么”，Skill 回答“应该怎么做”。**

Skill 与 Capability 在数据模型上并列，但 Skill 在执行关系上通常依赖 Capability。

```text
Task
  ↓ selects
Skill
  ↓ requires
Capability
  ↓ implemented by
Provider
```

### 6.1 Shadow 为什么必须管理 Skill

如果一个用户已经长期打磨出“如何做论文调研”“如何诊断服务器故障”“如何审查安全需求”这类方法，那么这些方法不应该被锁在 Claude Skill、Hermes Skill 或 DSH Plugin 中。

Shadow 需要负责：

- 规范化 Skill 表示；
- Skill 分层与组合；
- Skill Registry；
- 版本管理；
- provenance 与来源 Task；
- Runtime compatibility；
- Skill 选择与注入；
- Runtime-native Skill 的导入 / 投影；
- Skill 迁移与升级。

### 6.2 分层 Skill

当前概要设计采用四层概念：

| 层级 | 作用 | 示例 |
| --- | --- | --- |
| **策略级 Skill** | 高层方法论与长期工作方式 | 系统性调研、重大决策分析 |
| **领域级 Skill** | 某领域解决一类问题的方法 | 学术综述、服务器诊断、安全分析 |
| **程序级 Skill** | 可执行步骤、依赖、验证标准 | Linux IO 异常诊断流程 |
| **Runtime 投影** | 某 Runtime 的具体表达 | Claude Skill、Hermes Skill、DSH Plugin / Prompt |

前三层的规范化定义由 Shadow 持有。Runtime 投影可以变化和重新生成。

### 6.3 Skill 注入

不是所有 Skill 都进入 Runtime Context。

Task 形成 `SkillNeed`，Skill Resolver 根据：

- Task intent；
- 当前阶段；
- Skill 层级；
- Runtime 能力；
- 所需 Capability；
- Policy / Trust Profile；
- 历史验证结果；

选择合适 Skill，形成 `SkillBundle`，再由 Context Compiler 注入到对应 Runtime。

Skill 本身不授予权限。即使 Skill 声明需要 `server.restart`，最终调用仍然必须经过 Capability Gateway。

---

## 7. Capability、Provider 与 MCP

### 7.1 Capability

Capability 是**稳定、可治理、可版本化的动作或查询契约**。

例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

Runtime 面向 Capability 语义，而不是直接依赖某个 Provider 的私有 Tool 名称。

### 7.2 Provider

Provider 是 Capability 的具体实现者，例如：

```text
calendar.create
    ↓
Google Calendar Provider
```

Provider 可以更换，但 Capability 语义尽量稳定。

### 7.3 MCP 的位置

MCP 不属于 Capability 的子类型，也不是 Shadow 的长期资产本身。

> **Tool 是接口，Capability 是长期能力资产，Skill 是可复用经验，MCP 是协议。**

基本关系：

```text
Capability
   ↓ Provider Binding
Provider
   ↓ Transport / Adapter
MCP / REST / CLI / IPC / Local API
```

对 MCP 中不同对象的处理原则：

- **MCP Tool**：可以映射为 Capability Candidate 或 Provider Binding；
- **MCP Resource**：可以作为 Context Source / Evidence Source；
- **MCP Prompt**：可以作为 Skill Candidate、Runtime Template 或导入素材。

Shadow 未来也可以对 Runtime 暴露自己的 MCP Gateway，但所有具有副作用的调用仍必须进入 Capability Gateway，不能因为使用 MCP 就绕过治理。

---

## 8. Event、World State 与持续运行

Shadow 不围绕聊天 Session 运行，而围绕**事件和长期状态**运行。

```text
Email / Calendar / Home / Server / Files / User
                    ↓
                  Event
                    ↓
              Event Store
                    ↓
             World State
                    ↓
      Rule / Scheduler / Pulse
                    ↓
         Update / Notify / Task
```

Event 表示“发生了什么”；World State 表示“现在是什么状态”。

Runtime 默认看到与 Task 相关的紧凑 World State，而不是扫描所有历史 Event。

`Pulse` 可以作为低成本注意力机制，用极小模型或分类器过滤大量事件；它是运行优化策略，不是核心所有权模型。

---

## 9. Context Compiler

Context Compiler 是 Shadow 与不同 Runtime 之间的重要适配层。

输入可以包括：

```text
Task / Checkpoint
MemoryBundle
SkillBundle
World State
Policy / Trust Profile
Allowed Capabilities
Artifact / Evidence references
```

输出则转换为 Hermes、DSH、Claude、Codex 或未来 Runtime 能理解的具体上下文。

这样，Runtime 切换时不需要迁移其私有 Session 语义，只需要从 Shadow 规范化状态重新 hydrate。

---

## 10. Capability Gateway 与现实副作用

所有具有现实副作用的动作都必须经过统一链路：

```text
Runtime proposes
      ↓
Capability Gateway
      ↓
Identity / Schema
      ↓
Policy / Risk
      ↓
Approval if needed
      ↓
Idempotency
      ↓
Provider
      ↓
Execution Ledger / Audit
```

核心原则：

> **模型提出，Shadow 决定，Capability 执行。**

Runtime 成功执行外部动作后如果崩溃，恢复执行时必须通过 idempotency / ledger 判断动作是否已经完成，不能盲目重试。

---

## 11. 可替换组件的升级与迁移

“可替换”不仅意味着能接 Adapter，还意味着能够安全升级。

适用于 Runtime、Skill、Memory Engine 和 Provider 的长期方向：

```text
Candidate
  ↓
Compatibility Check
  ↓
Historical Replay / Test
  ↓
Canary
  ↓
Promote
  ↓
Rollback / Deprecate when needed
```

对于 Skill，迁移目标是**语义可移植**，不是保证 Runtime 私有实现逐字一致。

对于 Runtime，迁移目标是 Task Semantic Continuity。

对于 Memory Engine，核心 Canonical Memory 与 Raw Evidence 不能依赖某一引擎私有索引格式。

---

## 12. 持久化基线

V0.1 以 PostgreSQL 作为结构化持久状态的 Source of Truth。

当前需要长期考虑的逻辑对象包括：

```text
identity
event
world_state
task
checkpoint
artifact
memory
skill
skill_version
skill_relation
capability
provider
execution_ledger
runtime
runtime_binding
policy
approval
schedule
```

具体表结构暂不在概要设计阶段冻结。

Raw Evidence 和大型 Artifact 可以存放在本地文件系统或 NAS，数据库保存引用、hash、provenance 与 lifecycle metadata。

---

## 13. V0.1 范围

### 必须验证

- Event → World State；
- Shadow-owned Task / Checkpoint；
- 至少两个 Runtime 的 SRI 接入与语义接力；
- Raw Evidence / Canonical Memory / MemoryNeed；
- Skill Registry、基础分层、SkillNeed 和 Runtime Projection；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Ledger；
- Context Compiler 同时接收 MemoryBundle 与 SkillBundle；
- 基础 Scheduler / Event-driven execution；
- PostgreSQL 单机持久化。

### 暂不做

- 自研完整 Agent Loop；
- 自研 Browser Agent / Coding Agent；
- 完整 Workflow Engine；
- 自研 Vector DB / Graph DB；
- Plugin Marketplace；
- 完整聊天平台 / 语音平台；
- 多用户 SaaS；
- Kubernetes / 复杂微服务。

---

## 14. 当前架构原则

1. **Shadow 持有连续性。**
2. **Runtime 不拥有用户持久状态。**
3. **Task 属于 Shadow，Runtime 只执行。**
4. **Raw Evidence 是证据源；Canonical Memory 是可修正解释；索引可重建。**
5. **Memory Recall 是决策，不是简单数据库查询。**
6. **Skill 与 Capability 是并列的一等资产；Skill 使用 Capability。**
7. **Skill 描述方法，不授予权限。**
8. **Tool 是接口，Capability 是资产，Skill 是经验，MCP 是协议。**
9. **模型提出，Shadow 决定，Capability 执行。**
10. **Chat UI 只是 Client，不是系统核心。**
11. **分层智能是运行优化，不是最底层所有权原则。**
12. **逻辑模块化不等于微服务。**
13. **外围技术升级应尽量不修改核心长期资产。**
14. **已有 Runtime / Engine / Provider 能做好且不涉及长期连续性的功能，不在 Shadow 重造。**

---

## 15. 下一阶段

当前不继续展开过细的模块文档。

下一阶段先严格对齐并冻结以下核心契约：

```text
Task
Memory
Skill
Capability
Policy
SRI
Event / World State
Artifact
```

只有这些对象的定义、所有权和关系稳定后，再进入数据库 Schema、API、详细设计和代码实现。