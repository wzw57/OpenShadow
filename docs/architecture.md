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

基本规则：

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

这条可以作为架构自检：**如果移除 Memory 后系统只剩空壳，说明 Shadow 的边界设计错了。**

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
- Runtime、Skill、Provider 的迁移与升级元数据。

优先交给外部实现：

- Agent Loop / Planning；
- Runtime-native Skill discovery / activation / progressive disclosure / composition；
- Hermes、DSH、Claude、Codex 等 Runtime；
- Mem0、LangMem、Graphiti 等 Memory Engine；
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

跨 Runtime 接力迁移的是可验证语义状态，而不是：

- hidden chain-of-thought；
- KV Cache；
- Runtime 私有 Planner Graph；
- Runtime-specific Session object。

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
- Version；
- Provenance；
- Trust / Security metadata；
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

Shadow 决定某个 Runtime / 用户 / Task 可以使用哪些 Skill；Runtime 决定当前执行步骤什么时候激活哪一个。

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

Runtime Projection 可以删除、重新生成和覆盖，不是长期事实源。

如果 Runtime 修改或新建 Skill：

```text
Runtime Skill Change
      ↓
Candidate / Change Event
      ↓
Shadow import / review / normalize
      ↓
Canonical Skill update
```

Runtime 不得直接写 Canonical Skill Store。

### 5.5 可插拔 Skill Manager

V0.1 不把 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine 写进稳定核心。

如果后续真实使用证明 Runtime 的 Skill 选择能力不足，可以增加独立的 **Skill Manager**：

```text
Canonical Skill API
      ↑
Pluggable Skill Manager
      ↓
Runtime Skill Adapter
```

Skill Manager 可以负责高级检索、关系管理、冲突处理或路由，但它必须：

- 不拥有 Canonical Skill 唯一事实源；
- 可以被整体替换；
- 升级失败不破坏 Skill 资产；
- 不绕过 Runtime 和 Capability 的既有边界。

---

## 6. Memory 边界

Memory 采用三层模型：

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- Raw Evidence：保留事实来源与 provenance；
- Canonical Memory：当前可修正、带时间有效性的长期认知；
- Derived Layer：embedding、向量索引、摘要、图等，可删除重建。

Memory Engine 是可替换实现，不能拥有 Canonical Memory 的唯一事实源。

Shadow 后续可以通过 Memory Broker / Context Compiler 把任务相关记忆提供给 Runtime，但具体检索引擎可独立升级。

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
Relevant Memory
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

适用对象包括：

- Runtime；
- Memory Engine；
- Skill Manager；
- Runtime Skill Adapter；
- Provider；
- Protocol Adapter；
- Search / Index Engine。

升级原则：

> **新技术主要替换 Adapter、Manager 或派生表示，不迁移规范化个人资产。**

---

## 11. V0.1 架构范围

V0.1 只证明核心边界成立：

1. Event / World State；
2. Task / Semantic Checkpoint / Artifact；
3. Raw Evidence / Canonical Memory 基础闭环；
4. Skill Store + Version / Provenance / Trust + Runtime Projection / Sync；
5. SRI + 两个 Runtime Adapter；
6. Context Compiler；
7. Capability Registry / Gateway / Provider Binding；
8. Policy / Approval / Idempotency / Execution Ledger；
9. Scheduler / Event-driven execution；
10. PostgreSQL 本地持久化。

明确不要求：

- 自研 Agent Loop；
- 自研 Skill Resolver；
- Skill Graph Executor；
- Progressive Disclosure Engine；
- 完整 Workflow Engine；
- 自研 Browser / Coding Agent；
- 自研 Vector / Graph DB；
- 完整 Chat / Voice 平台。

---

## 12. 架构验收

| 验收 | 目标 |
| --- | --- |
| Runtime Continuity | Runtime A 失败后 Runtime B 继续同一 Task |
| Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| Skill Ownership | Runtime 修改 Projection 不直接修改 Canonical Skill |
| Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| Autonomous Operation | 无 Chat Prompt 时 Event / Scheduler 仍可触发 Task |
| Capability Governance | Runtime 无法绕过 Policy / Gateway 执行高风险动作 |
| Exactly-once Side Effect | Crash / Retry 不重复执行已完成动作 |

---

## 13. 当前待冻结边界

在进入 Schema 和 API 前，优先冻结：

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

详细 Skill 编排、Memory Router、Pulse 策略等均在核心边界冻结后按真实需求决定是否进入可插拔扩展层。