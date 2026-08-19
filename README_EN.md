# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models and runtimes are replaceable; durable user state, experience, and capabilities should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent. OpenShadow separates durable personal assets from any specific model or agent so that Hermes, DSH, Claude, Codex, and future runtimes can remain replaceable reasoning and execution resources.

## Why OpenShadow

Models change quickly, while a person's life, projects, experience, and ways of working remain continuous. Most personal AI systems still bind memory, tasks, tools, skills, and permissions to a product, session, or framework. Replacing a model, agent, or device often means rebuilding context, reconnecting tools, and teaching the system the same working methods again.

OpenShadow asks a different question:

> **If models, agent frameworks, and interfaces keep changing for the next decade, what should remain stable?**

Our answer is: **durable assets that belong to the user, are costly to recreate, and become more valuable through continued use.**

Those assets include identity and policies, task and project state, memory and raw evidence, reusable skills, real-world capabilities, and the long-term relationships among them.

## Core design

### 1. A stable continuity core owns durable personal state

OpenShadow separates a long-lived stable core from replaceable peripheral implementations.

The core owns objects that must remain consistent across models, runtimes, devices, sessions, and years. Models, agent runtimes, memory engines, tool protocols, and capability providers can continue to change.

The boundary rule is simple:

> **State that must remain stable and should not be migrated when implementation technology changes belongs to Shadow. Everything else should reuse mature external systems whenever possible.**

### 2. Shadow manages more than memory: tasks, skills, and capabilities are first-class assets

The core objects answer different questions:

| Object | Question | Shadow responsibility |
| --- | --- | --- |
| **Memory** | What do I know? | Preserve traceable long-term knowledge and its evidence |
| **Task** | What am I doing now? | Preserve goals, progress, checkpoints, and artifacts |
| **Skill** | How should this kind of work be done? | Manage, version, organize, migrate, and select reusable methods |
| **Capability** | What can the system actually do? | Define stable, governable action and query contracts |
| **Policy** | What is allowed? | Govern permission, risk, privacy, budget, and approval |

**Skill and Capability are peer first-class objects, but a Skill typically depends on Capabilities during execution.**

```text
Task
  ↓
Skill        "how to do it"
  ↓ uses
Capability   "what can be done"
  ↓ implemented by
Provider      "who implements it"
```

A Skill describes method; it does not grant authority. Real actions still pass through the Capability Gateway and Policy.

### 3. Skills are portable, hierarchical, durable assets

OpenShadow owns a canonical Skill representation instead of locking durable user knowledge into one runtime-specific Skill format.

Skills may exist at different abstraction levels:

- **Strategy Skill** — high-level methodology and long-lived working style;
- **Domain Skill** — how to solve a class of problems in a domain;
- **Procedure Skill** — more concrete steps, dependencies, and verification criteria;
- **Runtime Projection** — runtime-specific Skill representation for Hermes, DSH, Claude, Codex, or future systems.

A runtime may have native Skills, but if a Skill needs to survive across runtimes, the Shadow-owned canonical representation is the source of truth. Shadow selects Skills based on the task, abstraction level, and runtime capabilities, then injects or projects the appropriate Skill bundle into execution context.

Runtime migration therefore preserves **purpose, method, constraints, dependencies, verification criteria, and learned experience**, not proprietary prompt syntax or plugin structure.

### 4. Capability is a stable action contract; MCP is one integration protocol

A Capability is a durable, governable, executable contract such as:

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

A Capability is not the same thing as a Tool, and it is not the same thing as an MCP Tool. It defines **what the system can do**; the Provider and transport may change.

```text
Capability
  ↓
Provider
  ↓
MCP / REST / CLI / IPC / Local API
```

Therefore:

> **A Tool is an interface. Capability is a durable asset. Skill is reusable experience. MCP is a protocol.**

MCP can be an important integration path: an external MCP Tool may map to a Capability or Provider Binding; an MCP Resource may become a context or evidence source; an MCP Prompt may become a Skill candidate or runtime template. Shadow may also expose governed capabilities to runtimes through MCP instead of letting each runtime bypass Shadow and connect to external systems directly.

### 5. Tasks belong to Shadow; runtimes only execute them

Shadow stores canonical Tasks, artifacts, and semantic checkpoints. If a runtime fails, is upgraded, or is replaced, OpenShadow does not attempt to migrate hidden reasoning or private runtime internals. It preserves verifiable task semantics: goals, known facts, decisions and evidence, completed work, artifacts, remaining work, and side-effect state.

This allows a long-running Task to continue across different runtimes without tying personal continuity to a runtime Session.

### 6. Memory is decision support, not "vectorize everything"

OpenShadow separates memory into:

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes and Derived Views
```

Raw evidence preserves what happened. Canonical memory represents current, revisable, traceable interpretation. Vector indexes, summaries, and graph structures are derived and rebuildable.

Recall is driven by the decision needs of the active Task rather than naive vector top-k. When compressed memory is insufficient, Shadow can return to raw evidence and historical tasks.

### 7. The system runs around events and world state, not around a chat window

Shadow continuously receives events from email, calendars, files, servers, home devices, and other sources and maintains current World State. Tasks may be initiated by the user, by events, by schedules, or by changing conditions.

Even if every chat interface is removed, Shadow should still be able to update state, resume waiting tasks, invoke runtimes, execute capabilities, and record results.

Deterministic rules, a tiny local `Pulse`, and on-demand larger models may be used to reduce the cost of continuous operation. This is an engineering optimization, not OpenShadow's foundational design principle.

### 8. Real-world actions are governed centrally, and replaceable components must also be upgradeable

Real-world side effects pass through permission, risk, approval, idempotency, and a durable execution ledger. Runtime crashes and retries should not resend email, recreate calendar events, or repeat already-completed high-risk actions.

New Runtime versions, Memory Engines, Skill versions, and Providers should not simply overwrite the previous implementation. The long-term direction is compatibility checking, historical replay, canary validation, promotion, and rollback so that upgrades affect adapters and derived layers rather than forcing migration of core user assets.

> **Accumulate once; let future agents inherit it.**

Over time, OpenShadow aims to turn AI use from recurring consumption into **personal digital infrastructure that accumulates memory, skills, capabilities, experience, and governance**.

> **Ten years from now, the models may be completely different, but your AI should not need to meet you again—or relearn the working methods you already taught it.**

## Architecture overview

```text
Person / Digital World / Physical World
               │
               ▼
Interaction and Event Sources
Chat · Voice · Email · Calendar · Files · Devices · Servers
               │
               ▼
┌──────────────────────────────────────────────┐
│                 SHADOW CORE                  │
│            Stable Continuity Core            │
│                                              │
│ Identity / Policy      Events / World State  │
│ Tasks / Checkpoints    Memory                │
│ Skill Registry         Skill Resolver        │
│ Context Compiler       SRI / Runtime Registry│
│ Capability Registry / Gateway / Ledger       │
│ Scheduler / Pulse                            │
│                                              │
│ Durable assets:                              │
│ Memory · Task · Skill · Capability · Policy  │
│ History / State · Artifact                   │
└──────────────────────────────────────────────┘
               │
               ├─ Replaceable Runtimes
               │  Hermes · DSH · Claude · Codex · Future
               │
               ├─ Replaceable Memory Engines
               │  Mem0 · LangMem · Graphiti · Future
               │
               └─ Capability Providers
                  Home · PC · Server · Files · Email · Web
                  via MCP / REST / CLI / IPC / Local API
```

Core execution relationship:

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

## v0.1 MVP

The first release is not intended to be a complete personal AI product. Its purpose is to prove the continuity architecture.

### Core scope

- **Durable continuity** — Event, World State, Task, Checkpoint, Artifact, Raw Evidence, and Canonical Memory;
- **Skill management** — Skill Registry, hierarchical Skills, versioning, basic selection, and runtime Skill projection;
- **Runtime abstraction** — SRI, at least two Runtime adapters, Context Compiler, and cross-runtime semantic recovery;
- **Capability governance** — Capability Registry, Gateway, Provider Binding, Policy, Approval, Idempotency, and Execution Ledger;
- **Integration boundary** — at least one native Provider path with explicit MCP Adapter / Gateway boundaries reserved;
- **Persistent operation** — event-driven execution, Scheduler, waiting-task recovery, and low-cost Pulse;
- **Infrastructure** — PostgreSQL, rebuildable retrieval indexes, CLI / minimal admin entry point, and local single-node deployment.

### Must-pass demonstrations

| Scenario | Proof target |
| --- | --- |
| Runtime continuity | Runtime A fails; Runtime B continues the same Task from a semantic checkpoint |
| Skill portability | One canonical Skill can be projected to two runtimes while preserving its core method semantics |
| Cross-runtime memory | Durable Memory created through one Runtime can be correctly used by another |
| Autonomous event handling | Events can update state, create Tasks, and trigger execution without a chat prompt |
| Capability governance | A Runtime cannot bypass Policy and directly execute high-risk Provider actions |
| Side-effect safety | Crashes and retries do not repeat already-completed external actions |
| Runtime upgrade | Candidate Runtimes can be replayed, canaried, promoted, and rolled back without migrating core assets |

## Documentation

At this stage, the repository intentionally keeps only early design documents. Detailed design will be expanded again after the core concepts are strictly aligned.

- [Requirements Baseline](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

**Early design alignment / pre-MVP.**

The current priority is not adding more modules. It is freezing object definitions, ownership boundaries, and relationships. The next step is to align the core contracts for `Task / Memory / Skill / Capability / Policy / SRI` before database schema and implementation work begins.