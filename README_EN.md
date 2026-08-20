# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models, runtimes, and external ecosystems are replaceable; durable user state, experience, capabilities, and governance should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent. It does not reimplement reasoning, planning, skill activation, or tool orchestration that strong runtimes already provide. Shadow owns durable personal assets, task continuity, and governance boundaries so that Hermes, DSH, Claude, Codex, and future runtimes can remain replaceable execution engines.

## Core principles

> **State and contracts that must remain consistent across models, runtimes, devices, sessions, or years belong to Shadow. Everything else should reuse mature external systems whenever possible.**

> **Shadow owns durable work; Runtime owns execution decomposition.**

> **Shadow supervises execution; it does not plan execution.**

> **Shadow controls availability; Runtime controls Skill activation.**

> **Memory is available by default, not injected by default.**

> **Intelligence may be outsourced; authority may not.**

A Runtime may become smarter over time, but it must not become the sole source of truth for the user's durable state, permissions, or task continuity.

## Five logical domains

OpenShadow keeps only five top-level logical domains:

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

These are **responsibility and code boundaries, not five microservices**.

### 1. Task & Continuity

Owns continuity for durable work:

```text
Durable Task
Task Supervisor
Semantic Checkpoint
Runtime Checkpoint Ref
Runtime Binding
Handoff / Recovery
```

Runtime-internal subtasks, subagents, workflows, and planners remain inside the Runtime by default.

### 2. Memory & Personal Assets

Owns the user's accumulated long-lived assets:

```text
Raw Evidence
Canonical Memory
Task Working Memory
Canonical Skill
Version / Provenance / Trust
```

Memory Engines and Runtime-native Skill Engines are replaceable; Canonical Assets do not migrate with them.

### 3. Control & Governance

Owns Shadow's authoritative control:

```text
Policy
Capability
Approval
Idempotency
Execution Ledger
```

LLMs may assist semantic judgment, but they cannot directly commit authoritative Shadow state.

### 4. World State & Scheduler

Owns continuous operation:

```text
Event
World State
Scheduler
Condition
Background Jobs
```

Shadow can create or resume Tasks from events, schedules, and conditions even without a chat prompt.

### 5. Integration & Runtime Bridge

Owns the boundary to replaceable implementations:

```text
SRI / Runtime Adapter
Memory Engine Adapter
Provider Adapter
Model Adapter
Context / Hydration
```

Unified pattern:

```text
Shadow Contract
      ↓
Adapter
      ↓
Replaceable Implementation
```

## Task boundary

A Shadow Task is **Durable Work** that must survive beyond a Runtime Session or Planner. It is not a Runtime-internal task node.

A Runtime may freely create subtasks, invoke subagents, or build workflows. Internal work is promoted to a new Shadow Task only when it crosses a durability boundary, such as long waits, independent scheduling, cross-runtime survival, or user-level management.

Checkpoints have two layers:

- **Runtime Checkpoint** — runtime-specific and possibly opaque, for high-fidelity resume within the same Runtime;
- **Semantic Checkpoint** — runtime-neutral, for Runtime handoff, long pauses, or loss of native Runtime state.

A Runtime may propose progress or completion, but Shadow commits the durable Task state.

## Memory and Skill boundaries

Memory:

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Index / Summary / Graph
```

Shadow owns memory truth and access boundaries; Mem0, LangMem, Graphiti, MemOS, and similar systems provide replaceable Memory Intelligence.

Skill:

```text
Raw Skill Source
      ↓
Canonical Skill
      ↓
Runtime Projection
      ↓
Runtime-native execution
```

Shadow controls Skill availability; the Runtime controls discovery, activation, composition, and execution.

## Lightweight implementation principle

OpenShadow's complexity should live primarily in **semantic boundaries**, not runtime topology.

Recommended V0.1 physical shape:

```text
1 Shadow process
1 PostgreSQL
1 artifact directory
1 background worker
1 primary Runtime
several adapters
```

Internal communication defaults to ordinary function/service calls; PostgreSQL stores durable state; one worker handles background work. V0.1 does not require Kafka, RabbitMQ, Kubernetes, or a microservice architecture.

A possible code layout:

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

## What v0.1 must prove

The first release does not try to become a complete personal AI platform. It only needs to prove that:

1. Durable Tasks and personal assets survive the loss of a Runtime;
2. Runtime A can hand durable work to Runtime B through a Semantic Checkpoint;
3. Runtimes retain freedom over their own planners, subtasks, and Skill execution;
4. Memory Engines, Runtimes, and Providers can be replaced without migrating Canonical Assets;
5. Events and Scheduler can advance durable work without chat prompts;
6. Shadow can govern actions that cross into its authority domain and record external side effects;
7. Task / Control / Event / Runtime remain meaningful even when Memory is disabled.

V0.1 explicitly does not require a custom Agent Loop, synchronization of Runtime-internal subtask graphs, a full Workflow Engine, a custom Skill Resolver, a complex Intelligence Gateway, a multi-model routing platform, microservices, or multiple authoritative databases.

## Documentation

- [Requirements Baseline](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

**Early design alignment / pre-MVP.**

The current priority is to freeze a small number of critical contracts, not to keep adding top-level modules.