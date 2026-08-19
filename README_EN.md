# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models and runtimes are replaceable; durable user state should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent. Shadow separates identity, memory, tasks, capabilities, policies, history, and world state from any specific model or agent so that Hermes, DSH, Claude, Codex, and future runtimes can be used as replaceable reasoning and execution engines.

## Why OpenShadow

Models change quickly; a person's life, projects, and experience do not. Most personal AI systems still bind durable state to a product, session, or framework. Replacing a model, agent, device, or service often means rebuilding context, reconnecting tools, and restoring configuration.

OpenShadow focuses on a different question:

> **If models, agent frameworks, and interfaces keep changing for the next decade, what should remain stable?**

The answer is the durable state that truly belongs to the user:

- identity, preferences, constraints, and trust boundaries;
- active tasks, project state, and semantic checkpoints;
- traceable memory, raw history, and decision experience;
- connected devices, services, tools, and automations;
- the current state of the user's digital and physical environment.

These assets should remain usable by the next generation of models instead of disappearing with the previous one.

## Design vision

### 1. Continuity belongs to the user, not the runtime

Runtimes are responsible for reasoning and execution. Shadow remains the source of truth for tasks, memory, permissions, and history.

Switching from Hermes to DSH, or to a future runtime, should feel like replacing an execution engine rather than migrating an entire personal AI system.

### 2. The easier something is to replace, the farther it should be from the core

Models, prompts, retrieval engines, interfaces, and agent frameworks will continue to change rapidly. Raw history, task state, long-term policies, and personal capabilities are much harder to recreate.

OpenShadow therefore aims for a stable thin waist: fast-moving technology stays at the edge while durable user-owned state remains close to the core.

### 3. Always present, but intelligent on demand

Persistent operation does not require a large model to run continuously.

Shadow uses layered intelligence: deterministic rules handle obvious cases first; `Pulse` acts as a tiny always-on local attention layer; larger local models and specialist runtimes wake only when the situation is important, uncertain, or complex enough to justify them.

### 4. Capabilities should become reusable infrastructure

Once email, calendar, servers, files, or home devices are connected to Shadow, they should not belong to one particular agent.

New agents receive governed access through a common capability layer instead of rebuilding authentication, permissions, state, and tool integration from scratch.

> **Integrate once, reuse continuously. Build once, let future agents inherit it.**

Over time, OpenShadow aims to turn AI use from recurring consumption into **personal digital infrastructure that accumulates memory, capabilities, experience, and governance**.

> **Ten years from now, the models may be completely different, but your AI should not need to meet you again.**

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
│          Continuity & Control Layer          │
│                                              │
│ Identity / Policy      Events / World State  │
│ Tasks / Checkpoints    Memory Policy / Broker│
│ Context Compiler       Runtime Interface SRI │
│ Capability / Ledger    Scheduler / Pulse     │
│                                              │
│ Durable assets:                              │
│ Memory · Tasks · Capabilities · Policies     │
│ History · World State                        │
└──────────────────────────────────────────────┘
       │               │               │
       ▼               ▼               ▼
Replaceable        Replaceable      Capability
Runtimes           Memory Engines   Providers
Hermes / DSH       Mem0 / LangMem   Home / PC
Claude / Codex     Graphiti / FutureServer / Files
Future Runtime                      Email / Calendar / Web
       │               │               │
       └───────────────┴───────────────┘
                       │
                       ▼
         PostgreSQL · Raw Evidence · Artifacts
```

### Layered intelligence

```text
L0  Deterministic Rules
        │
        ▼
L1  Shadow Pulse
    Tiny local model / classifier, always on
        │
        ▼
L2  Local General Model
    Wakes on demand
        │
        ▼
L3  General or Specialist Runtime
    Hermes · DSH · Claude · Codex
```

`Pulse` is event-driven first. Heartbeats are used for reconciliation, recovery, and conditions without natural event sources; they are not periodic prompts to a large model asking whether anything needs attention.

## Core boundary

| Shadow owns | Reuse or outsource |
| --- | --- |
| Identity, policies, and trust boundaries | Agent loops and planning |
| Canonical tasks and semantic checkpoints | Hermes, DSH, Claude, Codex |
| Raw evidence and canonical memory contracts | Mem0, LangMem, Graphiti |
| Memory policy, broker, and context compilation | Vector, embedding, and graph implementations |
| Events and world state | Home Assistant and device drivers |
| Capability registry, gateway, and execution ledger | Email, calendar, browser, and server providers |
| SRI, runtime routing, and upgrade lifecycle | Model serving and model implementations |
| Long-lived schedules and Pulse policy | Chat platforms, speech stacks, and messaging gateways |

A simple rule determines the boundary:

> **State that must remain consistent across models, runtimes, devices, or years belongs to Shadow. Everything else should reuse mature external systems whenever possible.**

## v0.1 MVP

The first release is not intended to be a complete personal AI product. Its purpose is to prove that the continuity architecture works.

### Core scope

- **Durable continuity** — events, world state, tasks, semantic checkpoints, raw evidence, and canonical memory;
- **Dynamic execution** — deterministic rules, pluggable `Pulse`, event-driven wakeups, scheduling, and waiting-task recovery;
- **Runtime abstraction** — SRI, Hermes adapter, DSH adapter, and context compiler;
- **Capability governance** — registry, gateway, policy, approval, idempotency, and execution ledger;
- **Infrastructure** — PostgreSQL, pgvector, CLI, minimal admin interface, and local single-node deployment.

### Must-pass demonstrations

| Scenario | Proof target |
| --- | --- |
| Runtime continuity | A task interrupted in Hermes can continue in DSH from a semantic checkpoint |
| Cross-runtime memory | Durable memory created through one runtime can be correctly used by another |
| Autonomous event handling | Events can trigger decisions, tasks, and execution without a user prompt |
| Layered intelligence | Most low-value events terminate in rules or Pulse; only a small fraction escalate |
| Runtime upgrade | Candidate runtimes can be replayed, canaried, promoted, and rolled back without migrating user state |
| Task-aware memory | Retrieval is driven by decision relevance to the active task rather than naive vector top-k |
| Side-effect safety | Crashes and retries do not duplicate already-completed real-world actions |

## Documentation

### Product and system design

- [Requirements & System Design](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

### Detailed architecture

- [Layered Intelligence & Shadow Pulse](docs/architecture/intelligence.md)
- [Events & World State](docs/architecture/event-state.md)
- [Tasks & Semantic Checkpoints](docs/architecture/task.md)
- [Memory Architecture](docs/architecture/memory.md)
- [Runtime Architecture & Continuity](docs/architecture/runtime.md)
- [Capabilities & Governance](docs/architecture/capability.md)
- [Deployment Architecture](docs/architecture/deployment.md)

## Status

**Design baseline / pre-MVP.**

The product boundary and major dynamic architecture are now defined. The next phase is core contracts, detailed design, PostgreSQL schema, API design, and MVP implementation.
