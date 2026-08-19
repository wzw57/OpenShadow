# OpenShadow Architecture

This document describes the current v0.3 architecture baseline for OpenShadow.

## 1. Architectural intent

OpenShadow is deliberately designed as a **thin waist** between long-lived personal state and replaceable AI execution / memory / capability systems.

```text
Interaction / Event Sources
Chat · Voice · Email · Calendar · Home · Server · Devices
                         ↓
┌────────────────────────────────────────────────────────────┐
│                SHADOW CORE                                │
│        Personal AI Continuity & Control Layer             │
│                                                            │
│ Identity / Policy                                          │
│ Event → World State                                        │
│ Task → Semantic Checkpoint                                 │
│ Memory Policy → Memory Broker                              │
│ Context Compiler                                           │
│ SRI / Runtime Registry                                     │
│ Capability Registry → Gateway → Execution Ledger           │
│ Scheduler / Pulse                                          │
│                                                            │
│ Durable Assets:                                            │
│ Memory · Task · Capability · Policy · History / State      │
└────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
      Runtime Layer        Memory Engines      Capability Providers
 Hermes / DSH / Claude   Mem0 / LangMem /      HA / PC / Server /
       / Codex           Graphiti / Future      NAS / Email / Web
           ↓                    ↓                    ↓
      PostgreSQL · Event Store · Artifact Store · Raw Evidence
```

## 2. Ownership model

Shadow owns durable continuity. External systems own implementation details.

### Shadow owns

- Identity
- Event history
- World State
- Canonical Task
- Semantic Checkpoint
- Raw Evidence
- Canonical Memory Contract
- Memory Policy / Memory Broker
- Capability Contract / Registry
- Capability execution ledger
- Policy / Approval
- Runtime registry and binding
- Context compilation
- Long-lived schedules

### Runtime owns only temporary execution state

Runtime may own:

- Agent Loop
- planning
- hidden/internal reasoning
- temporary model context
- runtime-local Session
- runtime-specific subagents

Runtime must not be the source of truth for durable user state.

## 3. Module map

```text
shadow-core/
├── identity/
├── event/
├── world_state/
├── task/
├── checkpoint/
├── memory/
│   ├── contract/
│   ├── policy/
│   ├── broker/
│   └── feedback/
├── context/
├── runtime/
│   ├── sri/
│   ├── registry/
│   └── adapters/
├── capability/
│   ├── registry/
│   ├── gateway/
│   └── ledger/
├── policy/
├── scheduler/
└── pulse/
```

V0.1 should be a **modular monolith**, not a microservice system.

## 4. Core flow A — Event-driven task creation

```text
Server / Home / Calendar Event
            ↓
        Event Store
            ↓
      World State projection
            ↓
           Pulse
       ┌────┴────┐
       │         │
     Ignore   Create Task
                 ↓
            Task Manager
                 ↓
          Runtime Router / SRI
                 ↓
           Hermes / DSH
```

Purpose: prove Shadow is not a chat aggregator. It can react without a user prompt.

## 5. Core flow B — Task-aware memory recall

```text
Task + Current Step
        ↓
     MemoryNeed
        ↓
   Memory Broker
   ├─ structured lookup
   ├─ temporal query
   ├─ entity/relationship
   ├─ lexical / BM25
   └─ vector candidates
        ↓
      Rerank
        ↓
    MemoryBundle
        ↓
 Context Compiler
        ↓
      Runtime
```

Vector similarity is not the source of truth. Retrieval is an explicit decision about what memory could change the current next action.

## 6. Core flow C — Runtime handoff

```text
Shadow Task #N
     ↓ bind
  Hermes Session
     ↓
progress / artifacts / tool results
     ↓
Semantic Checkpoint
     ↓
Hermes fails / upgrade requested
     ↓
Shadow rebinds Task
     ↓
Context Compiler hydrates canonical state
     ↓
DSH Session
     ↓
continue Task
```

What must survive:

- goal
- current stage
- known facts
- decisions and evidence
- completed work
- artifacts
- tool results
- remaining work
- side-effect status

What does **not** need to survive:

- hidden reasoning chain
- runtime-private object graph
- token-by-token state
- runtime-local planner internals

## 7. Core flow D — Safe capability execution

```text
Runtime proposes action
        ↓
Capability Gateway
        ↓
Identity / schema validation
        ↓
Policy evaluation
        ↓
Approval gate (if required)
        ↓
Idempotency check
        ↓
Provider executes
        ↓
Result + Artifact
        ↓
Execution Ledger / Audit
        ↓
Runtime receives sanitized result
```

Key invariant:

> **LLM proposes; Shadow decides; Capability executes.**

### Exactly-once behavior

Every side-effect action receives an `action_id` / `idempotency_key`. If a Runtime crashes after execution, retrying the same action must return the previous result instead of executing it again.

## 8. Core flow E — Runtime upgrade

```text
Install Candidate Runtime
        ↓
SRI compatibility check
        ↓
Historical task dry-run replay
        ↓
Compare success / latency / cost / tool errors / safety
        ↓
Canary traffic
5% → 10% → 30% → 50% → 100%
        ↓
Promote
        ↓
Drain old Runtime
        ↓
Retire or rollback
```

The upgrade must not require moving Shadow Memory, Task, Capability, Policy or History.

## 9. Memory architecture

### 9.1 Raw Evidence

Raw Evidence stores what actually happened. Examples:

- conversations
- email
- calendar
- task trajectories
- provider results
- device / server events
- files and reports

Raw Evidence is retained independently of any current interpretation.

### 9.2 Canonical Memory

Canonical Memory is a structured interpretation of evidence and should include:

```text
memory_id
memory_type
entity / scope
content
valid_from / valid_to
confidence
importance
source_event_ids
supersedes
created_at
```

Typical types:

- semantic fact
- preference
- relationship
- episodic memory
- decision
- procedure
- project state

### 9.3 Derived intelligence

Embeddings, vector indexes, summaries, profiles, graph projections and reranker features are disposable and rebuildable.

## 10. Context Compiler

Shadow maintains a canonical context representation and compiles it for each Runtime.

```text
Task
+ Checkpoint
+ Task Working Memory
+ MemoryBundle
+ World State
+ Policy
+ Allowed Capabilities
+ Provenance
        ↓
 Context Compiler
        ├─ Hermes context
        ├─ DSH context
        ├─ Claude context
        └─ Future Runtime context
```

This is conceptually similar to an intermediate representation (IR): Shadow state remains stable while Runtime-specific formats can change.

## 11. Storage baseline

PostgreSQL is the V0.1 source of truth.

Suggested logical tables:

```text
users / identities
events
world_state
tasks
task_checkpoints
artifacts
memories
memory_links
memory_feedback
capabilities
providers
execution_ledger
runtimes
runtime_bindings
policies
approvals
schedules
```

`pgvector` is a derived retrieval index only.

Large artifacts and raw files may live on local filesystem / NAS while PostgreSQL stores references, hashes and metadata.

## 12. Trust boundaries

- Runtime never receives raw long-lived secrets.
- Cloud Runtime receives only Context allowed by its trust profile.
- Sensitive Raw Evidence / Memory can be local-only.
- Provider actions are always mediated by Capability Gateway.
- High-risk actions require approval.
- Every important state-changing action is auditable.

## 13. Replaceable components

| Component | Replace strategy |
| --- | --- |
| General Runtime | SRI Adapter |
| Specialist Agent | SRI / specialist adapter |
| Memory Engine | Memory Provider adapter |
| Vector / Search Engine | rebuild derived index |
| Home / PC / Server integration | Capability Provider |
| Messaging client | interaction adapter / webhook |
| LLM | Runtime / model configuration |

The architecture target is low **Upgrade Absorption Cost**: new technology should usually require a new adapter, not changes to durable core state.

## 14. Architectural guardrails

1. Shadow owns the continuity.
2. No runtime owns durable user state.
3. Raw evidence is truth; canonical memory is interpretation; indexes are disposable.
4. Retrieval is a decision, not a database query.
5. Task belongs to Shadow; Runtime only executes it.
6. LLM proposes; Shadow decides; Capability executes.
7. Fast deterministic actions do not require an Agent.
8. Logical modularity does not imply microservices.
9. Replaceable components must minimize upgrade absorption cost.
10. Do not rebuild functionality that existing Agent / Engine / Provider already does well unless continuity requires Shadow ownership.
