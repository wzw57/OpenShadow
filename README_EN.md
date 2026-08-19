# OpenShadow

[中文版](README.md) | **English**

> **Shadow owns the continuity.**  
> Models and runtimes are replaceable; durable user state should not disappear with them.

OpenShadow is a **local-first, runtime-neutral Personal AI Continuity & Control Layer**.

It is not another all-in-one agent. OpenShadow separates identity, memory, tasks, capabilities, policies, history, and world state from any specific model or agent. Hermes, DSH, Claude, Codex, and future runtimes are replaceable reasoning and execution resources.

## Why OpenShadow

Models change quickly, but a person's life, projects, and experience remain continuous. Most personal AI systems still bind durable state to a product, session, or framework, so replacing a model, agent, or device often means rebuilding context, reconnecting tools, and restoring configuration.

OpenShadow focuses on a different question:

> **If models, agent frameworks, and interfaces keep changing for the next decade, what should remain stable?**

The answer is the durable state that truly belongs to the user and is difficult to recreate:

- identity, preferences, constraints, and trust boundaries;
- active tasks, project state, and decision history;
- traceable memory, raw evidence, and task experience;
- connected devices, services, tools, and automations;
- the current state of the user's digital and physical world;
- long-lived policies, procedures, and permission structures.

These assets should remain usable by the next generation of models instead of disappearing with the previous one.

## Core design

### Continuity belongs to the user; runtimes only execute

Shadow is the long-term source of truth for tasks, memory, policies, history, and capabilities. Runtimes may own temporary sessions, planning state, and internal context, but they must never become the sole owner of durable user state.

Switching from Hermes to DSH, or to a future runtime, should feel like replacing an execution engine rather than migrating an entire personal AI system.

### Shadow is a stable thin waist

The easier a component is to replace, the farther it should sit from the core; the more personal and difficult it is to recreate, the closer it should sit to the core.

Models, prompts, retrieval engines, interfaces, and agent frameworks can change quickly, while core contracts, personal state, raw history, and governance remain stable. Ideally, adopting a new generation of technology should mean adding an adapter or replacing a peripheral implementation rather than migrating a person's digital life.

### The system runs around events and world state, not around a chat window

Shadow continuously receives events from email, calendars, files, servers, home devices, and other sources, then projects “what happened” into “what is true now.” Tasks may be initiated by the user, but they may also be triggered by events, schedules, or changing conditions.

Even with every chat interface removed, Shadow should still be able to maintain world state, resume waiting tasks, invoke runtimes, execute capabilities, and record results.

To keep continuous operation inexpensive, the system may use deterministic rules, a tiny local `Pulse`, and on-demand larger models as layered execution strategies. This is an optimization strategy, not the fundamental ownership boundary of Shadow.

### Tasks belong to Shadow and can move across runtimes semantically

Shadow stores canonical tasks, artifacts, and semantic checkpoints. When a runtime fails, is upgraded, or is replaced, Shadow does not attempt to migrate hidden reasoning or private runtime internals. It transfers verifiable task semantics instead: goals, known facts, decisions and evidence, completed work, artifacts, remaining work, and side-effect state.

This allows the same long-running task to continue across different runtimes over time.

### Memory is not “vectorize everything”

Shadow separates memory into three layers:

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Rebuildable Indexes and Derived Views
```

Raw evidence preserves what actually happened. Canonical memory represents the current traceable interpretation. Vector indexes, summaries, graphs, and other retrieval structures are derived and rebuildable.

Recall is also not defined as naive vector top-k. Shadow derives an explicit memory need from the active task, prefers structured, temporal, and entity-aware retrieval paths, and can fall back to deep inspection of raw history when compressed memory is insufficient.

### Capabilities belong to the user, and actions are governed centrally

Once email, calendar, servers, home devices, and files are connected to Shadow, they become reusable capabilities rather than private tools owned by a particular agent.

Every action with a real-world side effect passes through a common policy, approval, idempotency, and audit path:

```text
Model proposes an action
        ↓
Shadow evaluates permission and risk
        ↓
Approval / Idempotency / Execution Ledger
        ↓
Capability provider executes
```

A runtime crash and retry should therefore not resend the same email, recreate the same calendar event, or repeat another already-completed external action.

### Replaceability also means upgradeability

Runtimes, memory engines, and capability providers should have explicit replacement boundaries. A candidate runtime can be checked for compatibility, replayed against historical tasks, evaluated through canary traffic, promoted gradually, and rolled back without migrating the user's memory, tasks, capabilities, or policies.

OpenShadow aims for low **upgrade absorption cost**: new technology should mostly affect adapters and peripheral implementations rather than forcing repeated rewrites of the core.

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
               │
               ├─ Replaceable runtimes
               │  Hermes · DSH · Claude · Codex · Future runtimes
               │
               ├─ Replaceable memory engines
               │  Mem0 · LangMem · Graphiti · Future engines
               │
               ├─ Capability providers
               │  Home · PC · Servers · Files · Email · Calendar · Web
               │
               ▼
PostgreSQL · Raw Evidence · Artifacts · Execution Ledger
```

## Core boundary

| Shadow owns | Reuse or outsource |
| --- | --- |
| Identity, policies, and trust boundaries | Agent loops and planning |
| Canonical tasks, semantic checkpoints, and artifacts | Hermes, DSH, Claude, Codex |
| Raw evidence and canonical memory contracts | Mem0, LangMem, Graphiti |
| Memory policy, broker, and context compilation | Vector, embedding, and graph implementations |
| Events, world state, and long-lived schedules | Home Assistant and device drivers |
| Capability registry, gateway, and execution ledger | Email, calendar, browser, and server providers |
| SRI, runtime routing, handoff, and upgrades | Model serving and model implementations |
| Pulse policy | Chat platforms, speech stacks, and messaging gateways |

The boundary rule is simple:

> **State that must remain consistent across models, runtimes, devices, or years belongs to Shadow. Everything else should reuse mature external systems whenever possible.**

## v0.1 MVP

The first release is not intended to be a complete personal AI product. Its purpose is to prove that the continuity architecture works.

### Core scope

- **Durable continuity** — events, world state, tasks, semantic checkpoints, artifacts, raw evidence, and canonical memory;
- **Tasks and runtimes** — SRI, Hermes adapter, DSH adapter, context compilation, and cross-runtime semantic recovery;
- **Memory** — write policy, task-aware recall, memory bundles, and deep recall of raw history;
- **Capabilities and governance** — registry, gateway, policy, approval, idempotency, and execution ledger;
- **Persistent operation** — event-driven execution, scheduling, waiting-task recovery, and a low-cost Pulse mechanism;
- **Infrastructure** — PostgreSQL, pgvector, CLI, minimal admin interface, and local single-node deployment.

### Must-pass demonstrations

| Scenario | Proof target |
| --- | --- |
| Runtime continuity | A task interrupted in Hermes can continue in DSH from a semantic checkpoint |
| Cross-runtime memory | Durable memory created through one runtime can be correctly used by another |
| Autonomous event handling | Events can update state, create tasks, and trigger execution without a user prompt |
| Runtime upgrade | Candidate runtimes can be replayed, canaried, promoted, and rolled back without migrating user state |
| Task-aware memory | Recall is driven by decision relevance to the active task and can fall back to raw history |
| Side-effect safety | Crashes and retries do not duplicate already-completed real-world actions |

## Documentation

### Product and system design

- [Requirements & System Design](docs/requirements.md)
- [Architecture Overview](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

### Detailed architecture

- [Events & World State](docs/architecture/event-state.md)
- [Tasks & Semantic Checkpoints](docs/architecture/task.md)
- [Memory Architecture](docs/architecture/memory.md)
- [Runtime Architecture & Continuity](docs/architecture/runtime.md)
- [Capabilities & Governance](docs/architecture/capability.md)
- [Layered Intelligence & Shadow Pulse](docs/architecture/intelligence.md)
- [Deployment Architecture](docs/architecture/deployment.md)

## Status

**Design baseline / pre-MVP.**

The product boundary and major dynamic architecture are now defined. The next phase is core contracts, detailed design, PostgreSQL schema, API design, and MVP implementation.
