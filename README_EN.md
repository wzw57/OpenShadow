# OpenShadow

[中文版](README.md) | **English**

> **Shadow is a personal AI designed to persist and evolve over time.**

OpenShadow is a local-first, implementation-independent platform for personal AI assets and capabilities. The user interacts with one continuous Shadow while agent runtimes, models, memory intelligence, runners, routers, databases, providers, voice systems, and other implementations remain replaceable.

The goal is not to rebuild AI infrastructure. OpenShadow keeps a minimal stable core and composes strong external projects through versioned adapters, allowing the user's assets and understanding of current reality to evolve over the long term.

## Product model

~~~text
Shadow
├─ Shadow Core
│  ├─ Domain Contracts
│  ├─ Authority & State Transition
│  ├─ Task Continuity
│  ├─ World State
│  ├─ Execution Dispatch
│  ├─ Extension / Integration Registry
│  └─ Portability & Upgrade
│
├─ Replaceable Components
│  ├─ Agent Runtimes / Model Workers
│  ├─ Deterministic Runners / Routers
│  ├─ Memory Intelligence / Durable Store
│  ├─ Search / Index / Skill System
│  ├─ Asset and State Source Connectors
│  ├─ Capability Providers
│  └─ Voice / User Interfaces
│
└─ User-owned Assets
   ├─ Tasks / Runs / Checkpoints
   ├─ Canonical Memories / World State
   ├─ Owner / Personal Space / Home Space
   ├─ Skills / Executable Assets
   ├─ Extensions / Integrations
   ├─ Asset Catalog / Artifacts
   └─ Policies / Action History
~~~

Shadow is the complete product. Shadow Core is only the smallest part that must remain stable.

## Confirmed principles

### Every request goes through Shadow, but not necessarily an Agent Runtime

Every Request accepted by Shadow creates one Root Run; rejected admission creates only a minimal Admission Record. Shadow uses an explicit Execution Binding to dispatch work to an Agent Runtime, a bounded Model Worker, a Deterministic Runner, or a Capability Provider. Full prompts, outputs, and tool traces are retained according to user policy and durable value. Only work that must survive sessions, execution targets, waiting conditions, or long periods becomes a Durable Task.

### Shadow owns assets, continuity, current state, and authority

A runtime, memory engine, model, database-specific format, or provider must not become the irreplaceable owner of the user's long-term assets or authoritative state.

### Replaceable components own intelligence and execution

Reasoning, planning, routing, memory extraction and consolidation, retrieval, script execution, speech processing, device protocols, and provider execution should use replaceable implementations.

### Adapters are first-class architecture

OpenShadow defines Port Contracts, the Adapter SDK, manifests, permissions, version negotiation, health contracts, and contract tests. Concrete adapters and implementations can evolve independently.

## World State and reality synchronization

Shadow maintains a minimal World State that expresses its current accepted view of reality; it is not a complete digital twin.

~~~text
Calendar / Weather / Device / Location / User
                     ↓
          Replaceable Source Adapter
                     ↓
       Observation Proposal + timestamp + TTL
                     ↓
          Shadow validates and commits
                     ↓
      World State: fresh / stale / unknown
~~~

External systems collect and retain domain data. Shadow stores only portable state projections, provenance, timestamps, freshness, and relationships. A Source Adapter cannot directly modify authoritative state. Shadow refreshes sources when needed and explicitly represents stale or unknown information instead of pretending that all state is real-time.

World State differs from Memory: Memory is durable historical knowledge, World State is a time-sensitive current belief, an Event records what happened, and a Task records a future commitment.

Accepted World State is portable Canonical State. Shadow retains the current projection, conflicting candidates, evidence, and expiry reason, while applying type-specific retention to Observations. Explicit user statements have the highest source priority without freezing state forever; newer and more reliable Observations may replace them. Complex fusion is proposed by a replaceable State Resolver.

## Flexible execution plane

Shadow supports four replaceable Execution Targets:

| Target | Purpose |
|---|---|
| Agent Runtime | Open-ended, multi-step work requiring planning or tool loops |
| Model Worker | One bounded inference such as classification, extraction, or summarization |
| Deterministic Runner | Scripts, functions, and fixed programs |
| Capability Provider | External APIs, accounts, devices, and real-world actions |

Core owns admission, permissions, budgets, Binding validation, status, and result records. Advanced task classification, multi-model scoring, and dynamic selection are proposed by a replaceable Routing Component. Early implementations can use explicit user choices and static rules.

Scripts are durable Executable Assets with stable identity, version, input/output contracts, dependencies, permissions, provenance, and checksums. Language runtimes, dependency resolution, isolation, and execution belong to replaceable Runners.

A Runtime operates freely inside a Capability Envelope issued by Shadow. Crossing its data, capability, resource, side-effect, budget, or validity boundary requires renewed authorization. Shadow does not retain private Runtime reasoning, but it records minimal Usage or Action Records at adapter, budget, and side-effect boundaries.

## Heartbeat and Semantic Pulse

System health heartbeat is deterministic. Process checks, adapter health, leases, timeouts, and scheduler ticks do not depend on a model.

An optional small model may act as a Semantic Pulse. It can periodically inspect authorized Events, World State, and recent activity, then propose recall, state updates, Runs, Durable Tasks, or escalation to a stronger target. It cannot directly commit authoritative state, bypass policy or budgets, or become necessary for correct operation.

## Memory boundary

Canonical Memory created during long-term use belongs to Shadow and must survive replacement of memory intelligence.

~~~text
Conversation / Task / External Source
                 ↓
       Replaceable Memory Intelligence
                 ↓
          Memory Candidate
                 ↓
       Shadow validates and commits
                 ↓
      Primary Durable Store Adapter
                 ↓
       Replaceable Database Engine
~~~

Shadow owns stable memory identity, provenance, scope, versions, and commit semantics. External components provide extraction, consolidation, retrieval, reranking, embeddings, graphs, and other fast-moving intelligence.

The database engine is also replaceable. Shadow defines the Durable Store Port, canonical records, migrations, exports, and integrity checks.

## External information and capability assets

Shadow does not copy and permanently manage all external information. For Notion, Obsidian, Drive, email, file systems, and similar sources, the Asset Catalog normally records existence, location, Integration, availability, and provenance relationships. Content is read through a Connector only when needed.

Users accumulate capabilities as well as information:

~~~text
Capability Assets
├─ Skills / Executable Assets
├─ Extensions / Integrations
├─ MCP connections
├─ Provider bindings
├─ Runtime / Model / Runner profiles
└─ Configuration / permission metadata
~~~

These assets need stable identities, versions, provenance, configuration, permissions, compatibility, and migration metadata so they remain reusable when models, runtimes, and devices change.

## Durable governance, local-first, and failure boundaries

Every Canonical Asset has an explicit Owner and Space from the first version. An Owner may be a User or Space. Personal assets can belong to a User, while shared room and household device state can belong to a Home Space. The near-term implementation only creates a default Personal Space and implicit Home Space; it does not implement membership, roles, invitations, or sharing.

Core enforces four stable data classes: public, personal, sensitive, and restricted. Unknown data defaults to sensitive. A Model Binding declares accepted data classes, Memory, World State, and external asset boundaries, plus retention, training, and regional constraints. External classifiers may raise protection but cannot lower it on their own.

Deleting Canonical Memory defaults to recoverable logical deletion followed by policy-controlled physical erasure. Corrections preserve version relationships by default, while sensitive history can be fully erased. A common Erasure Request tracks deletion across adapters and reports unconfirmed components as pending or unreachable.

Local-first means user control, portability, and verifiability rather than a fixed physical location. A standard export excludes secrets and rebuildable state. A separately authorized and encrypted full-device backup may include secrets, checkpoints, and selected derived state.

When the Primary Durable Store is unavailable, Shadow may continue clearly marked read-only and ephemeral interaction, but it pauses Canonical Commits and blocks real-world side effects by default. Only preconfigured emergency capabilities may first commit to a reliable local persistent Outbox, execute, and reconcile after recovery.

## Current boundary

OpenShadow does not build database engines, general agent loops, foundation models, intelligent routing algorithms, memory intelligence, vector or graph databases, script runtimes and sandboxes, speech engines, browser agents, coding agents, device protocol stacks, or domain-specific digital twins.

OpenShadow must implement:

- Shadow Domain Contracts;
- the authoritative state commit boundary;
- Task and Run continuity;
- minimal Observation, World State, Owner, and Space semantics;
- Data Classification, Retention, and Erasure semantics;
- Capability Envelopes;
- Execution Dispatch and Binding;
- the Adapter SDK and Extension Registry;
- Integration and Capability Binding;
- the policy enforcement point;
- portable data formats;
- compatibility, migration, and integrity verification;
- user control APIs.

Near-term implementation focuses on a single-user path without making future multi-user or multi-device support impossible.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Core / External Responsibility Matrix](docs/responsibility-matrix.md)
- [Key Use Cases](docs/use-cases/README.md)
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

**The Stage 2 key-use-case draft is complete and ready for consolidated review.**

Eighteen use cases now cover admission, multi-device Web interaction, execution, continuity, Memory, World State, external actions, Store failure, migration, erasure, Integrations, on-demand asset access, and Semantic Pulse. After review, Stage 3 will freeze domain objects, relationships, aggregates, and state machines.
