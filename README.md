# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 持有连续性。**  
> 模型和运行时可以替换，属于用户的长期状态、经验与能力不应该随之消失。

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它不试图成为另一个“大而全”的智能体，而是把应该长期存在的个人资产从具体模型和智能体中解耦出来，让 Hermes、DSH、Claude、Codex 以及未来出现的新运行时都成为可替换的推理与执行资源。

## 为什么需要 OpenShadow

模型更新很快，但人的生活、项目、经验和工作方法是长期连续的。今天大多数个人 AI 系统仍然把记忆、任务、工具、技能和权限绑定在某个产品、会话或框架里，因此换模型、换智能体、换设备，往往意味着重新建立上下文、重新配置工具，甚至重新教一遍“应该怎么做”。

OpenShadow 关注的不是“怎样再做一个更聪明的助手”，而是：

> **如果未来十年模型、智能体框架和交互方式不断变化，哪些东西应该一直留下来？**

我们的答案是：**属于用户、难以重新获得、并且会随着使用不断积累的长期资产。**

这些资产包括身份与规则、任务与项目状态、记忆与历史证据、可复用技能、现实世界能力，以及这些资产之间的长期关系。

## 核心设计

### 1. 稳定核心层持有个人连续性

OpenShadow 将系统分成一个长期稳定的核心层和一组可替换的外围实现。

核心层持有那些必须跨模型、跨运行时、跨设备、跨会话甚至跨年份保持一致的对象；模型、智能体运行时、记忆引擎、工具协议和能力提供者则可以持续替换。

判断标准很简单：

> **必须长期保持一致、并且替换底层技术时不应该迁移的状态，属于 Shadow；其余功能优先复用成熟系统。**

### 2. Shadow 管理的不只是记忆，还包括任务、技能和能力

几个核心对象回答的是不同问题：

| 对象 | 回答的问题 | Shadow 的职责 |
| --- | --- | --- |
| **Memory** | 我知道什么？ | 保存可追溯的长期认知与证据关系 |
| **Task** | 我现在要完成什么？ | 保存目标、进度、检查点和任务产物 |
| **Skill** | 这类事情应该怎么做？ | 管理、版本化、分层组织、迁移和选择可复用方法 |
| **Capability** | 系统实际上能做什么？ | 定义稳定、可治理的动作与查询契约 |
| **Policy** | 什么可以做、什么不可以做？ | 统一权限、风险、隐私、预算和审批 |

其中，**Skill 和 Capability 是两个并列的一等对象，但 Skill 在执行上通常依赖 Capability。**

```text
Task
  ↓
Skill        “怎么做”
  ↓ uses
Capability   “能做什么”
  ↓ implemented by
Provider      “由谁实现”
```

Skill 描述方法，不授予权限；真正执行动作时仍然必须经过 Capability Gateway 和 Policy。

### 3. Skill 是可迁移、可分层的长期资产

OpenShadow 负责持有规范化 Skill，而不是把用户长期积累的方法锁在某个 Runtime 的 Skill 格式里。

Skill 可以按抽象程度分层：

- **策略级 Skill**：高层方法论与长期工作方式；
- **领域级 Skill**：某一领域如何解决某类问题；
- **程序级 Skill**：更具体的步骤、依赖与验证标准；
- **Runtime 投影**：为 Hermes、DSH、Claude、Codex 等运行时生成的具体 Skill 表达。

Runtime 可以拥有自己的原生 Skill，但如果某个 Skill 需要跨 Runtime 长期保留，Shadow 的规范化表示才是事实源。Shadow 根据任务、当前层级和 Runtime 能力选择需要的 Skill，并把合适的 Skill 组合或投影注入到执行上下文中。

这意味着更换 Runtime 时，迁移的是**目标、方法、约束、依赖、验证标准和经验语义**，而不是某个 Runtime 私有的提示词格式或插件结构。

### 4. Capability 是稳定能力契约，MCP 只是接入协议之一

Capability 表示用户拥有的稳定、可治理、可执行能力，例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

Capability 不等于 Tool，也不等于某个 MCP Tool。它描述“系统能做什么”；具体由哪个 Provider、通过什么协议实现，可以变化。

```text
Capability
  ↓
Provider
  ↓
MCP / REST / CLI / IPC / Local API
```

因此：

> **工具只是接口，Capability 是长期能力资产，Skill 是可复用经验，MCP 是协议。**

MCP 可以作为重要的集成方式：外部 MCP Tool 可以映射为 Capability 或 Provider Binding；MCP Resource 可以成为上下文或证据来源；MCP Prompt 可以作为 Skill Candidate 或 Runtime 模板。Shadow 也可以通过 MCP 向 Runtime 暴露经过统一治理的能力，而不是让每个 Runtime 直接绕过 Shadow 连接外部系统。

### 5. Task 属于 Shadow，Runtime 只负责执行

Shadow 保存规范化 Task、任务产物和语义检查点。运行时失败、升级或被替换时，不迁移隐藏思维链或私有内部状态，而是迁移可验证的任务语义：目标、已知事实、决策依据、完成进度、任务产物、剩余工作和副作用状态。

因此，同一个长期任务可以从一个 Runtime 接力到另一个 Runtime，而不用把个人状态绑定在某个 Session 上。

### 6. Memory 是决策基础，不是“把历史全部向量化”

Shadow 将记忆区分为：

```text
原始证据
   ↓
规范化记忆
   ↓
可重建的索引与派生层
```

原始证据负责保存事实来源；规范化记忆表达当前可修正、可追溯的认知；向量索引、摘要和图结构只是可重建的派生结果。

记忆召回围绕当前 Task 的决策需要进行，而不是默认取向量相似度最高的若干历史。必要时可以继续回溯原始证据和历史任务。

### 7. 系统围绕事件和世界状态运行，而不是围绕聊天窗口运行

Shadow 持续接收邮件、日历、文件、服务器、家庭设备等事件，并维护当前 World State。任务可以由用户发起，也可以由事件、调度或条件变化触发。

即使删除聊天界面，Shadow 仍然应该能够更新状态、恢复等待任务、调用 Runtime、执行 Capability 并记录结果。

为了降低全天候运行成本，可以使用确定性规则、极小本地 `Pulse` 和按需唤醒的大模型做分层处理；这是一种工程优化，不是 OpenShadow 的最底层设计原则。

### 8. 所有现实动作统一治理，所有可替换组件都应该可升级

具有现实副作用的动作统一经过权限、风险、审批、幂等与执行台账。运行时崩溃和重试不应该造成重复发送邮件、重复创建日历或重复执行高风险操作。

新的 Runtime、Memory Engine、Skill 版本和 Provider 也不应该“直接覆盖上线”。长期方向是支持兼容性检查、历史任务回放、灰度验证、晋升和回滚，使技术升级尽量只影响适配层和派生层，而不迁移用户的核心资产。

> **一次积累，被未来所有智能体继承。**

长期来看，OpenShadow 希望把 AI 使用从一种持续消费的服务，逐渐变成一种能够积累**记忆、技能、能力、经验和治理规则**的个人数字基础设施。

> **十年后模型已经完全不同，但你的 AI 不需要重新认识你，也不需要重新学习你已经教会它的做事方法。**

## 架构概览

```text
人 / 数字世界 / 物理世界
          │
          ▼
交互与事件入口
聊天 · 语音 · 邮件 · 日历 · 文件 · 设备 · 服务器
          │
          ▼
┌──────────────────────────────────────────────┐
│               SHADOW CORE                    │
│             稳定连续性核心层                  │
│                                              │
│ 身份 / Policy       Event / World State      │
│ Task / Checkpoint   Memory                    │
│ Skill Registry      Skill Resolver            │
│ Context Compiler    SRI / Runtime Registry    │
│ Capability Registry / Gateway / Ledger        │
│ Scheduler / Pulse                            │
│                                              │
│ 长期资产：                                    │
│ Memory · Task · Skill · Capability · Policy  │
│ History / State · Artifact                    │
└──────────────────────────────────────────────┘
          │
          ├─ 可替换 Runtime
          │  Hermes · DSH · Claude · Codex · Future
          │
          ├─ 可替换 Memory Engine
          │  Mem0 · LangMem · Graphiti · Future
          │
          └─ Capability Provider
             Home · PC · Server · Files · Email · Web
             via MCP / REST / CLI / IPC / Local API
```

核心执行关系：

```text
Task
 ├─ MemoryNeed → Memory
 ├─ SkillNeed  → Skill Resolver → Skill Bundle
 │
 ▼
Context Compiler
 ▼
Runtime
 ▼
Capability Gateway
 ▼
Capability → Provider
```

## v0.1 最小可行版本

第一版不追求完整的个人 AI 产品，只验证这套连续性架构是否成立。

### 核心范围

- **连续性状态**：Event、World State、Task、Checkpoint、Artifact、Raw Evidence、Canonical Memory；
- **Skill 管理**：Skill Registry、分层 Skill、版本与基础选择机制、Runtime Skill 投影；
- **Runtime 抽象**：SRI、至少两个 Runtime Adapter、Context Compiler、跨 Runtime 语义恢复；
- **Capability 与治理**：Capability Registry、Gateway、Provider Binding、Policy、Approval、Idempotency、Execution Ledger；
- **集成协议**：至少支持一种原生 Provider 接入，并预留 MCP Adapter / Gateway 边界；
- **持续运行**：事件驱动、Scheduler、等待任务恢复和低成本 Pulse；
- **基础设施**：PostgreSQL、可重建检索索引、CLI / 最小管理入口、本地单机部署。

### 必须通过的验证

| 场景 | 验证目标 |
| --- | --- |
| Runtime 连续性 | Runtime A 中断后，Runtime B 能从语义检查点继续同一个 Task |
| Skill 可迁移性 | 同一规范化 Skill 能投影到两个不同 Runtime 并保持核心方法语义 |
| 跨 Runtime Memory | 一个 Runtime 形成的长期 Memory 能被另一个 Runtime 正确使用 |
| 自主事件处理 | 没有聊天提示时，Event 也能更新状态、创建 Task 并触发执行 |
| Capability 治理 | Runtime 不能绕过 Policy 直接执行高风险 Provider 动作 |
| 副作用安全 | 崩溃与重试不会重复执行已经完成的现实动作 |
| Runtime 升级 | 候选 Runtime 可回放、灰度、晋升和回滚，而核心资产无需迁移 |

## 文档

当前阶段只保留前期设计文档，详细设计将在核心概念严格对齐后重新展开。

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

**前期设计对齐 / MVP 实现前。**

当前重点不是继续增加模块，而是先冻结对象定义、所有权边界和对象之间的关系。下一阶段会优先对齐 `Task / Memory / Skill / Capability / Policy / SRI` 等核心契约，再进入数据库结构和实现。