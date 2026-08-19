# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models, runtimes, and external ecosystems are replaceable; durable user state, experience, capabilities, and governance should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent, and it does not reimplement reasoning, planning, skill activation, or tool orchestration that strong runtimes already provide. Shadow owns durable personal assets, task continuity, and governance boundaries so that Hermes, DSH, Claude, Codex, and future runtimes can remain replaceable execution engines.

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

The core objects answer different questions:

| Object | Question | Shadow responsibility |
| --- | --- | --- |
| **Task** | What am I doing now? | Preserve goals, progress, checkpoints, artifacts, and side-effect state |
| **Memory** | What do I know? | Preserve traceable, revisable long-term knowledge and evidence |
| **Skill** | How should this kind of work be done? | Own, version, migrate, and distribute reusable methods |
| **Capability** | What can the system actually do? | Define stable, governable action and query contracts |
| **Policy** | What is allowed? | Govern permission, risk, privacy, budget, and approval |
| **Event / World State** | What happened, and what is true now? | Let the system persist beyond a chat window |

Even with Memory temporarily removed, Shadow should still be able to:

- persist and resume Tasks / Semantic Checkpoints;
- hand work across different Runtimes;
- own and synchronize Skills;
- govern Capabilities, Policies, Approvals, and the Execution Ledger;
- ingest Events, maintain World State, and run the Scheduler;
- preserve Artifacts, history, and external side-effect state.

Without those responsibilities, Shadow really would collapse into a memory engine.

### 3. Tasks belong to Shadow; runtimes only reason and execute

A Runtime may own temporary Sessions, planning state, and internal context, but it must not become the durable source of truth for a Task.

When a Runtime fails, is upgraded, or is replaced, Shadow transfers verifiable semantic state: goal, known facts, decision evidence, completed work, Artifacts, remaining work, and side-effect state—not hidden reasoning or private Runtime objects.

> **Task belongs to Shadow; Runtime executes it.**

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

Shadow does not need to rebuild the Skill execution engine already provided by Hermes and other capable Runtimes.

**Shadow owns:**

- Canonical Skill identity and raw Skill source;
- Version / Provenance / Trust;
- user-level enablement, disablement, and visibility scope;
- Runtime compatibility;
- Runtime Projection / sync state;
- import, export, migration, and rollback;
- candidate ingestion for Skills created or modified by a Runtime.

**Runtime owns:**

- Skill discovery;
- per-task Skill activation;
- progressive disclosure;
- Skill composition and orchestration;
- runtime-native bundles, prompts, and references;
- runtime-internal tool-use strategy.

In short:

> **Shadow controls availability; Runtime controls activation.**

Runtime-specific Skill representations are disposable projections. A Skill learned or modified by a Runtime first becomes a Candidate; it cannot directly mutate the Canonical Skill asset.

If real-world evidence later shows that Runtime-level Skill selection is insufficient, Shadow may add a **pluggable Skill Manager** for advanced retrieval, relationship management, or routing. That manager remains replaceable and does not become part of the stable core.

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

All real-world side effects still pass through the Capability Gateway, Policy, Approval, Idempotency, and Execution Ledger. Native MCP or tool-calling support must not allow a Runtime to bypass Shadow governance.

### 6. Memory is a decision substrate, not long-term RAG

OpenShadow separates:

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes / Summaries / Graphs
```

Raw Evidence preserves what happened. Canonical Memory represents current, revisable, traceable interpretation. Vector indexes, summaries, and graphs are derived and rebuildable.

A Memory Engine may be replaced, but it must not own the only authoritative copy of Canonical Memory.

### 7. Shadow runs around Events, World State, and Tasks—not around a chat window

Tasks may come from a user, an Event, a Schedule, or a changing Condition. Even if every Chat UI is removed, Shadow should still maintain World State, resume waiting Tasks, select a Runtime, execute governed Capabilities, and record results.

Rules, `Pulse`, and local small models may reduce the cost of continuous operation, but they are implementation strategies rather than core ownership principles.

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
│ Task / Checkpoint       Memory Authority      │
│ Skill Authority         Runtime Registry / SRI│
│ Context Compiler        Scheduler             │
│ Capability Registry / Gateway / Ledger        │
│ Artifact / History                            │
└──────────────────────────────────────────────┘
               │
               ├─ Replaceable Runtimes
               │  Hermes · DSH · Claude · Codex · Future
               │
               ├─ Replaceable Engines / Managers
               │  Memory Engine · optional Skill Manager
               │
               └─ Replaceable Providers / Protocols
                  Home · PC · Server · Email · Files · Web
                  MCP · REST · CLI · IPC · Local API
```

Skill path:

```text
Canonical Skill Store
        │
        ├─ version / provenance / trust / scope
        │
        ▼
Runtime Skill Adapter
        │
        ▼
Disposable Runtime Projection
        │
        ▼
Runtime
  discovery / activation
  disclosure / composition
  execution
        │
        ▼
usage / change events
        │
        ▼
Shadow
```

## What Shadow owns vs. what external systems implement

| Shadow owns / governs | Replaceable implementation |
| --- | --- |
| Task / Semantic Checkpoint | Agent Loop / Planning |
| Raw Evidence / Canonical Memory | Memory Engine / Search Engine |
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
- Task / Semantic Checkpoint / Artifact;
- Raw Evidence / Canonical Memory minimum loop;
- **Skill Store, Version / Provenance / Trust, Runtime Projection / Sync**;
- SRI, at least two Runtime adapters, and Context Compiler;
- Capability Registry / Gateway / Provider Binding;
- Policy / Approval / Idempotency / Execution Ledger;
- Scheduler / Event-driven execution;
- PostgreSQL + local-first single-node deployment.

V0.1 does **not** require a custom Skill Resolver, Skill Graph Executor, Progressive Disclosure Engine, or full Workflow Engine. The first step is to validate whether Runtime-native Skill discovery, selection, and orchestration are already sufficient.

### Must-pass demonstrations

| Scenario | Proof target |
| --- | --- |
| Runtime continuity | Runtime A fails; Runtime B continues the same Task |
| Skill portability | One Canonical Skill can be synchronized/projected to two Runtimes |
| Skill ownership | Runtime edits to a Projection cannot directly mutate the Canonical Skill |
| Cross-runtime Memory | Runtime B can use durable Memory created through Runtime A |
| Autonomous event handling | Events can update state, create Tasks, and trigger execution without chat prompts |
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

The current priority is to freeze which assets Shadow must own durably and which execution responsibilities should remain in Runtime / Engine / Provider layers. Database schema, APIs, and detailed implementation follow only after that boundary is stable.