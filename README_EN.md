# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models, runtimes, and external ecosystems are replaceable; durable user state, experience, capabilities, and governance should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent, and it does not reimplement reasoning, planning, skill activation, or tool orchestration that strong runtimes already provide. Shadow owns durable personal assets, task continuity, supervision, and governance boundaries so that Hermes, DSH, Claude, Codex, and future runtimes can remain replaceable execution engines.

## Why OpenShadow

Models and agent frameworks change quickly, while a person's life, projects, experience, and ways of working remain continuous. Most personal AI systems still bind Memory, Task, Skill, Tool, and permissions to a specific product, Session, or Runtime. Replacing the technology stack often means rebuilding context, restoring tasks, reconnecting tools, and teaching the same working methods again.

OpenShadow asks a longer-term question:

> **If models, runtimes, tool protocols, and interfaces keep changing for the next decade, what should remain stable?**

Our answer is: **canonical personal assets that belong to the user, are costly to recreate, and compound through continued use.**

These include Task, Memory, Skill, Capability, Policy, Event / World State, Artifact, and the durable relationships and history around them.

## Core principles

### 1. Shadow may depend on external ecosystems for implementation, but must not depend on them to own canonical personal assets

OpenShadow separates a **stable core** from **replaceable implementations**.

Models, Runtimes, Memory Engines, Skill execution mechanisms, Providers, and protocols such as MCP may change. Durable sources of truth should not have to migrate with them.

> **State and contracts that must remain consistent across models, runtimes, devices, sessions, or years belong to Shadow. Everything else should reuse mature external systems whenever possible.**

External formats may be used for import, export, adapters, or derived projections, but they must not become the authoritative long-term source of truth.

### 2. Shadow is not a Memory Engine

Memory is only one subsystem of Shadow.

| Object | Question | Shadow responsibility |
| --- | --- | --- |
| **Task** | What durable work am I committed to completing? | Own Durable Work, checkpoints, artifacts, and side-effect state |
| **Memory** | What do I know? | Preserve traceable, revisable long-term knowledge and evidence |
| **Skill** | How should this kind of work be done? | Own, version, migrate, and distribute reusable methods |
| **Capability** | What can the system actually do? | Define stable, governable action and query contracts |
| **Policy** | What is allowed? | Govern permission, risk, privacy, budget, and approval |
| **Event / World State** | What happened, and what is true now? | Let the system persist beyond a chat window |

Even with Memory temporarily removed, Shadow should still persist and resume Tasks, supervise long-running execution, hand work across Runtimes, synchronize Skills, govern Capabilities and Policies, maintain Events / World State / Scheduler, and preserve Artifacts and side-effect state.

### 3. Shadow owns durable work; the Runtime owns execution decomposition

A Shadow Task is **Durable Work** that must survive beyond a Runtime Session or Planner. It is not a Runtime-internal task node.

> **Shadow owns durable work; Runtime owns execution decomposition.**

A Runtime may freely create subtasks, subagents, workflows, DAGs, or use any planning architecture it prefers. Those internal structures stay inside the Runtime by default. Internal work is promoted to a new Shadow Task only when it crosses a durability boundary, such as requiring cross-session or cross-runtime survival, long waits, independent scheduling, independent Policy / Budget, or user-level management.

Shadow acts as a control plane above the Runtime:

> **Shadow supervises execution; it does not plan execution.**

The Task Supervisor uses deterministic checks first for Runtime health, timeout, deadline, retry, schedule, Artifact, Approval, Ledger, and side-effect state. A replaceable Semantic Verifier is used only when deterministic checks are insufficient; high-risk or subjective decisions can escalate to Human Approval.

A Runtime may report progress or propose completion, but Shadow commits the durable state:

> **Runtime proposes progress and completion; Shadow commits durable task state.**

Checkpoints have two layers. A Runtime Checkpoint may be an opaque native Session / Planner State reference for high-fidelity resume within the same Runtime. A Semantic Checkpoint is runtime-neutral recovery state used for Runtime handoff, long pauses, or loss of Runtime-native state.

> **Shadow defines durability boundaries; Runtime retains freedom over its internal state model.**

Shadow therefore does not migrate hidden chain-of-thought, KV cache, or Runtime-private planner graphs, and does not prescribe checkpointing every fixed number of execution steps.

### 4. Skill assets belong to Shadow; Skill execution belongs to the Runtime

Skill and Capability are peer first-class objects:

```text
Task
  ↓
Skill         "how to do it"
  ↓ uses
Capability    "what can be done"
  ↓ implemented by
Provider       "who implements it"
```

Shadow owns Canonical Skill, raw source, Version / Provenance / Trust, Scope, Runtime compatibility, Projection / Sync, import/export, and migration. The Runtime owns discovery, activation, progressive disclosure, composition, and execution.

> **Shadow controls availability; Runtime controls activation.**

Runtime-specific Skill representations are disposable projections. Skills learned or modified by a Runtime first become Candidates; they cannot directly mutate Canonical Skill assets.

### 5. Capability is a durable action contract; MCP is only a protocol

A Capability defines stable, governable action or query semantics, for example:

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

The Provider and transport may change between MCP, REST, CLI, IPC, or a local API.

> **A Tool is an interface. Capability is a durable asset. Skill is reusable experience. MCP is a protocol.**

All real-world side effects still pass through Capability Gateway, Policy, Approval, Idempotency, and Execution Ledger.

### 6. Memory is available by default, not injected by default

OpenShadow separates:

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes / Summaries / Graphs
```

Owning a large amount of Memory does not mean every Task performs recall. A Runtime raises a semantic Recall Intent only when historical information may matter. Shadow then controls Scope, Privacy, Validity, and Context Budget before querying replaceable Memory Engines.

> **Shadow owns memory truth and access boundaries; external Memory Engines provide extraction, retrieval, consolidation, and association intelligence.**

Current default implementation direction:

- **Shadow + PostgreSQL** — source of truth for Raw Evidence, Canonical Memory, and Task Working Memory;
- **Mem0 OSS** — first online recall / candidate retrieval backend;
- **LangMem** — background extraction / consolidation candidate generation;
- **Graphiti** — second-stage experiment for a derived temporal Memory Graph and multi-hop association;
- **MemOS** — later evaluation as an alternative Memory Engine.

All of these sit behind adapters and remain replaceable. Derived indexes, summaries, and graphs are rebuildable.

The long-term Memory goal is not to maximize recall volume, but to:

> **Automatically provide the smallest amount of relevant Memory sufficient to improve the current decision while consuming as little Runtime attention as possible.**

### 7. Shadow runs around Events, World State, and Tasks—not around a chat window

Tasks may come from a user, an Event, a Schedule, or a changing Condition. Even if every Chat UI is removed, Shadow should still maintain World State, supervise and resume waiting Tasks, select a Runtime, execute governed Capabilities, and record results.

Rules, `Pulse`, and local small models may reduce continuous-operation cost, but they are implementation strategies rather than core ownership principles.

## Architecture overview

```text
Person / Digital World / Physical World
               │
               ▼
Interaction / Event Sources
               │
               ▼
┌──────────────────────────────────────────────┐
│                 SHADOW CORE                  │
│             Stable Continuity Core           │
│                                              │
│ Identity / Policy       Event / World State  │
│ Durable Task / Supervisor / Checkpoint       │
│ Memory Authority        Skill Authority      │
│ Runtime Registry / SRI  Context Compiler     │
│ Scheduler               Capability Gateway   │
│ Execution Ledger        Artifact / History   │
└──────────────────────────────────────────────┘
               │
               ├─ Replaceable Runtimes
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

## What Shadow owns vs. what external systems implement

| Shadow owns / governs | Replaceable implementation |
| --- | --- |
| Durable Task / Supervisor / Semantic Checkpoint | Runtime Planner / Subtask / Workflow |
| Runtime Checkpoint Reference / Binding | Runtime-native Session / Checkpoint implementation |
| Raw Evidence / Canonical Memory / Task Working Memory | Mem0 / LangMem / Graphiti / Search Engine |
| Canonical Skill / Version / Provenance | Runtime-native Skill Engine / optional Skill Manager |
| Capability Contract / Policy / Ledger | Provider / MCP Server / Tool implementation |
| Event / World State / Scheduler | Event adapters / notification channels |
| Runtime Registry / SRI / Binding | Hermes / DSH / Claude / Codex |
| Context Compiler | Runtime-specific prompt / context representation |
| Artifact / audit history | Storage backend implementation |

## v0.1 MVP

The first release exists to validate continuity and ownership boundaries, not to build a complete personal AI platform.

### Core scope

- Event / World State;
- Durable Task / Task Supervisor;
- Runtime Checkpoint Reference / Semantic Checkpoint / Artifact;
- deterministic-first Task supervision;
- Raw Evidence / Canonical Memory / Task Working Memory;
- Memory Access API + Mem0 Adapter;
- basic LangMem background Memory Candidate / Consolidation experiment;
- Skill Store, Version / Provenance / Trust, Runtime Projection / Sync;
- SRI, at least two Runtime adapters, and Context Compiler;
- Capability Registry / Gateway / Provider Binding;
- Policy / Approval / Idempotency / Execution Ledger;
- Scheduler / Event-driven execution;
- PostgreSQL + local-first single-node deployment.

V0.1 does **not** require a custom Runtime Planner, synchronization of Runtime-internal subtask graphs, a custom Skill Resolver, Skill Graph Executor, Progressive Disclosure Engine, Learned Memory Router, or full Workflow Engine. Graphiti association and Semantic Verifier remain later experiments rather than part of the default critical path.

### Must-pass demonstrations

| Scenario | Proof target |
| --- | --- |
| Durable Task ownership | Runtime-internal planning and subtasks remain private while Durable Task state survives independently |
| Task supervision | Shadow can deterministically wait, retry, resume, request checkpoints, and commit completion |
| Runtime continuity | Runtime A fails; Runtime B continues from Semantic Checkpoint + durable state |
| Runtime-native resume | The original Runtime can resume with high fidelity from an opaque Runtime Checkpoint / Session reference |
| Completion ownership | Runtime proposes completion; Shadow commits the Durable Task state |
| Skill portability | One Canonical Skill can be synchronized/projected to two Runtimes |
| Skill ownership | Runtime edits to a Projection cannot directly mutate the Canonical Skill |
| Cross-runtime Memory | Runtime B can use durable Memory created through Runtime A |
| Memory selectivity | Simple Tasks can perform no recall; history-dependent Tasks receive only a small relevant set |
| Memory Engine replaceability | Replacing the online retrieval Engine does not migrate Canonical Memory |
| Autonomous event handling | Events / Scheduler / Supervisor can advance Tasks without chat prompts |
| Capability governance | A Runtime cannot bypass Policy / Gateway for high-risk actions |
| Side-effect safety | Crash / retry does not repeat already-completed actions |

## Documentation

At this stage the repository intentionally keeps only early design documents. Detailed design will be expanded after the core boundaries are frozen.

- [Requirements Baseline](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

**Early design alignment / pre-MVP.**

The current priority is to freeze which assets Shadow must own durably, which control responsibilities belong to Shadow, and which execution responsibilities should remain in Runtime / Engine / Provider layers. Database schema, APIs, and detailed implementation follow only after that boundary is stable.