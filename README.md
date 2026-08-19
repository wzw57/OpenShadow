# OpenShadow

> **Personal AI Continuity & Control Layer**

OpenShadow（品牌名：**The Shadow**）是一个 **Local-first、Runtime-neutral** 的个人 AI 连续性与控制层。

它不试图成为另一个“全能 Agent”。Shadow 负责长期持有用户的 **Memory、Task、Capability、Policy 与 History / World State**，而 Hermes、DeepSeek Harness、Claude / Codex 以及未来 Agent Runtime 只负责推理和执行。

> **Shadow owns the continuity.**  
> Runtime owns reasoning and execution — never durable user state.

## Why OpenShadow

今天的个人 AI 状态通常被锁在具体 Agent / Session / Framework 内：更换 Runtime 往往意味着重新迁移记忆、任务、工具、配置和上下文。OpenShadow 的目标是把这些长期资产从执行引擎中解耦，让底层 Agent 可以升级、失败、替换甚至消失，而个人连续性仍然存在。

同时，OpenShadow 不希望为了“常驻 AI”而持续运行一个昂贵的大模型 Agent。系统采用**分层智能与按需升级**：普通代码和规则先处理确定性事件，极小本地模型 Pulse 负责 7×24 注意力判断，更大的本地模型和 Agent Runtime 只在真正需要时被唤醒。

## Core principles

- **Thin Core, Deep Responsibility** — Core 尽可能小，只持有必须跨 Runtime、跨模型、跨设备、跨年份保持一致的状态。
- **Runtime-neutral** — Agent Runtime 是可替换执行器，不拥有持久用户状态。
- **Local-first** — 个人原始数据、记忆和控制状态默认本地持有。
- **User-owned continuity** — Memory、Task、Capability、Policy、History 属于用户，而不是某个 Agent。
- **Raw evidence first** — 原始证据是长期事实源；Canonical Memory 可修正；索引和派生层可重建。
- **Retrieval is a decision** — 记忆调取围绕当前 Task / Step 的决策价值，而不是默认向量 Top-K。
- **Layered intelligence** — 智能越昂贵，越晚进入执行路径；Fast Path 不强制调用 Agent。
- **Smallest sufficient attention** — 7×24 常驻注意力层使用最小足够智能，Pulse 目标为 0.5B–3B 级可替换本地模型 / 分类器，而不是高频 heartbeat 大 Agent。
- **LLM proposes, Shadow decides** — 高风险动作必须经过统一 Policy / Approval / Idempotency / Audit。

## Architecture

### Continuity layer

```text
Interaction / Events
Chat · Voice · Email · Calendar · Home · Server · Devices
                         ↓
┌─────────────────────────────────────────────────────┐
│ SHADOW CORE — Continuity & Control Layer           │
│                                                     │
│ Identity / Policy                                   │
│ Event → World State                                 │
│ Task → Semantic Checkpoint                          │
│ Memory Policy → Memory Broker                       │
│ Context Compiler                                    │
│ SRI / Runtime Registry                              │
│ Capability Registry → Gateway → Execution Ledger    │
│ Scheduler / Pulse                                   │
│                                                     │
│ Durable assets:                                     │
│ Memory · Task · Capability · Policy · History/State │
└─────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
 Replaceable Runtime   Memory Engines      Capability Providers
 Hermes / DSH /        Mem0 / LangMem      HA / PC / Server /
 Claude / Codex        Graphiti / Future   NAS / Email / Web
```

### Layered intelligence

```text
User Intent / Events
        ↓
L0 Deterministic Rules
        │
        ├─ handled → Fast Path / State Update
        │
        └─ meaningful / uncertain
                 ↓
L1 Shadow Pulse
Tiny local model / classifier
Target: 0.5B–3B class, always-on
                 │
        ├─ Ignore / Update / Notify
        │
        └─ needs richer reasoning
                 ↓
L2 Local General Brain
                 │
        └─ complex multi-step work
                 ↓
L3 Runtime / Specialist
Hermes · DSH · Claude · Codex
```

Pulse is **event-driven first**. Heartbeat exists for reconciliation and conditions without natural events; it does not mean repeatedly asking a large Agent whether something needs attention.

## What Shadow owns

| Shadow 持有 | 优先复用 / 外包 |
| --- | --- |
| Identity / Policy | Agent Loop / Planning |
| Canonical Task / Semantic Checkpoint | Browser Agent |
| Raw Evidence / Canonical Memory Contract | Embedding / Vector DB / Graph Engine |
| Memory Policy / Memory Broker | Mem0 / LangMem / Graphiti |
| Event / World State | Home Assistant 设备驱动 |
| Capability Registry / Gateway / Ledger | Email / Calendar / Browser / Server Provider |
| SRI / Runtime Router / Upgrade | Hermes / DSH / Claude / Codex |
| Context Compiler | AstrBot / Hermes Gateway / IM |
| Scheduler / Pulse policy | STT / TTS / LLM Serving / Pulse model implementation |

## v0.1 MVP

V0.1 只验证连续性层与动态运行机制是否成立：

1. Event Store / World State Projection
2. L0 Rules + pluggable tiny Pulse + event-driven wakeup
3. Fast Path that bypasses General Runtime
4. Canonical Task / Semantic Checkpoint / Task Working Memory
5. Memory Contract / Memory Policy / Memory Broker / MemoryBundle / Deep Recall
6. SRI + Hermes Adapter + DSH Adapter
7. Context Compiler
8. Capability Registry / Gateway / Execution Ledger
9. Policy / Approval / Idempotency
10. Scheduler / waiting-task resume
11. PostgreSQL + pgvector
12. Minimal Web Console / CLI
13. Docker Compose / local-first single-node baseline

### Must-pass demos

- **Runtime Continuity** — Hermes 执行中的 Task 可通过 Semantic Checkpoint 由 DSH 接力恢复。
- **Cross-runtime Memory** — 一个 Runtime 形成的长期 Memory 能被另一个 Runtime 按任务需要调用。
- **Autonomous Event Handling** — 无用户 Prompt 时，事件可触发 L0 / Pulse → Task → Runtime → Capability。
- **Layered Intelligence** — 大量低价值事件由 L0 / Pulse 消化，仅少量任务升级到昂贵 Runtime。
- **Runtime Upgrade** — Candidate Runtime 经 replay / canary 后切换，Memory / Task / Capability / Policy 不迁移。
- **Task-aware Memory** — 相比普通 Vector Top-K，减少无关上下文并改善任务决策；必要时可 Deep Recall 原始历史。
- **Side-effect Safety** — Runtime 崩溃恢复后，不重复执行已完成的外部副作用。

## Documentation

### Product / overview

- [Requirements & System Design](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

### Detailed architecture

- [Intelligence Plane & Shadow Pulse](docs/architecture/intelligence.md)
- [Event & World State](docs/architecture/event-state.md)
- [Task & Semantic Checkpoint](docs/architecture/task.md)
- [Memory Architecture](docs/architecture/memory.md)
- [Runtime Architecture & Continuity](docs/architecture/runtime.md)
- [Capability & Governance](docs/architecture/capability.md)
- [Deployment Architecture](docs/architecture/deployment.md)

## Status

**Design baseline / pre-MVP.** 当前产品边界与主要动态架构已经收敛，下一阶段进入 Core Contracts、LLD、PostgreSQL schema、API 与 MVP 实现。
