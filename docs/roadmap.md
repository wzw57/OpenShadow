# OpenShadow Roadmap

This roadmap follows the current v0.3 requirements baseline. The goal is to ship a usable continuity layer quickly and avoid turning OpenShadow into another all-in-one Agent platform.

## Phase 0 — Freeze contracts

Before building UI or integrations, freeze the first version of the durable contracts.

### Deliverables

- Event Contract
- Task / TaskEnvelope Contract
- Semantic Checkpoint Contract
- Memory Contract
- Capability Contract
- Policy / Approval Contract
- SRI (Shadow Runtime Interface)
- Canonical Context Contract
- Artifact reference format
- Execution Ledger / idempotency model

### Exit criteria

- Each contract has a version field.
- No contract depends on Hermes / DSH private types.
- Durable fields and replaceable / derived fields are clearly separated.

---

## Phase 1 — Persistence & task spine

Build the smallest durable core.

### Build

- Python + FastAPI modular monolith
- PostgreSQL migrations
- Event Store
- Minimal World State projection
- Task Store
- Semantic Checkpoint Store
- Artifact metadata store
- Execution Ledger
- Structured logging

### First tables

```text
identities
events
world_state
tasks
task_checkpoints
artifacts
execution_ledger
```

### Exit criteria

- Shadow Core restart does not lose Task / Event / Ledger state.
- Task can be created, paused, checkpointed and resumed without any Agent Runtime.

---

## Phase 2 — First Runtime integration

Use Hermes as the first stable general Runtime.

### Build

- SRI v0.1
- Runtime Registry
- Hermes Adapter
- Runtime binding on Task
- Minimal Context Compiler
- Runtime health / status

### Demo

```text
Task created in Shadow
      ↓
Context compiled
      ↓
Hermes executes
      ↓
results / artifacts written back to Shadow
```

### Exit criteria

- Hermes cannot become the source of truth for Task state.
- Hermes Session may disappear while the Shadow Task still exists.

---

## Phase 3 — Memory minimum loop

Implement useful memory without building a full Memory OS.

### Build

- Raw Evidence storage
- Canonical Memory table
- Memory Candidate extraction
- Simple Memory Policy
- MemoryNeed
- Memory Broker
- MemoryBundle
- Task Working Memory
- memory_feedback

### Retrieval baseline

1. structured lookup
2. temporal validity
3. entity matching
4. lexical / BM25
5. vector candidate search

### Experiment baseline

Compare:

- no memory
- full recent history
- vector top-k
- Shadow task-aware recall

Metrics:

- task success
- irrelevant context
- token usage
- user correction rate
- decision quality

### Exit criteria

- Memory injection is driven by Task / Step need, not every prompt.
- Every Canonical Memory item has provenance.
- Derived indexes can be deleted and rebuilt.

---

## Phase 4 — Capability governance

Add one real capability provider and prove safe side-effect handling.

### Start with

- `server.status.read`
- `server.logs.read`

Then add a reversible or approval-gated action such as:

- `server.service.restart`

### Build

- Capability Registry
- Capability Gateway
- risk levels
- Policy evaluation
- Approval gate
- action_id / idempotency_key
- result sanitization
- Execution Ledger integration

### Exit criteria

- Runtime cannot call Provider directly.
- Retrying a successful action does not execute it twice.
- Audit trail explains who proposed, why it was allowed and what happened.

---

## Phase 5 — Runtime handoff

Integrate DSH as a second Runtime and prove Runtime-neutral continuity.

### Build

- DSH Adapter
- Canonical Task hydration
- Runtime switch / rebind
- last durable checkpoint recovery
- failure handling

### Killer demo

```text
Hermes executes Task to 50%
        ↓
checkpoint
        ↓
kill Hermes
        ↓
DSH receives canonical Task state
        ↓
DSH continues and finishes
```

Must preserve:

- Task goal and stage
- facts / decisions
- artifacts
- provider results
- side-effect ledger
- remaining work

### Exit criteria

**AC-01 Runtime Continuity** passes.

---

## Phase 6 — Pulse & autonomous flow

Prove that Shadow is not a chat aggregator.

### Build

- Scheduler
- Pulse L0 deterministic rules
- optional L1 tiny local model
- Event → World State → Pulse → Task flow
- notification output

### Demo

```text
Server warning event
      ↓
World State changes
      ↓
Pulse evaluates
      ↓
Task created automatically
      ↓
Runtime investigates
      ↓
Shadow records result
```

### Exit criteria

The entire flow works without a user chat prompt.

---

## Phase 7 — Runtime evaluation & upgrade

Turn Runtime replaceability into an operational feature.

### Build

- Runtime candidate status
- historical task replay
- dry-run / sandbox mode
- runtime evaluation metrics
- traffic weight / canary routing
- promotion / rollback
- drain behavior

### Evaluation metrics

- task success
- cost / tokens
- latency
- tool error rate
- manual intervention rate
- safety violations
- checkpoint / resume quality

### Exit criteria

A candidate Runtime can be evaluated and promoted without migrating Shadow durable assets.

---

## Phase 8 — Personal deployment

Run OpenShadow continuously for real use.

### Goals

- accumulate real Events
- accumulate real Task trajectories
- observe Memory usefulness
- observe handoff failures
- refine Policy boundaries
- measure operational reliability

### Research data worth keeping

- memory candidate decisions
- memory recall decisions
- injected vs actually used memories
- task outcomes
- runtime handoff outcomes
- provider retries / idempotency events
- user corrections

This real-world dataset becomes the basis for later research rather than blocking product development up front.

---

# v0.1 acceptance matrix

| ID | Acceptance scenario | Target |
| --- | --- | --- |
| AC-01 | Runtime Continuity | Hermes interrupted → DSH resumes and completes |
| AC-02 | Cross-Runtime Memory | Runtime B can use Memory created through Runtime A |
| AC-03 | Autonomous Event Handling | Event can trigger Task without chat prompt |
| AC-04 | Exactly-once Side Effect | Runtime retry does not duplicate external action |
| AC-05 | Runtime Upgrade | Replay + canary + promote without migrating durable assets |
| AC-06 | Memory Utility | Task-aware recall reduces irrelevant context vs top-k baseline |

# Explicit non-goals for v0.1

Do **not** spend MVP time on:

- a custom Agent Loop
- a custom browser Agent
- a custom Coding Agent
- a full RAG framework
- a custom vector database
- a graph database unless experiments prove it necessary
- a full chat platform
- a full voice assistant
- a Home Assistant replacement
- a plugin marketplace
- multi-user SaaS
- Kubernetes / production microservice decomposition

# Recommended implementation order

1. Freeze contracts.
2. Design PostgreSQL schema and migrations.
3. Implement Event / Task / Checkpoint / Ledger core.
4. Implement SRI + Hermes Adapter + minimal Context Compiler.
5. Implement the minimal Memory write / recall loop.
6. Implement Capability Gateway + one provider.
7. Implement DSH Adapter + handoff demo.
8. Implement Scheduler / Pulse autonomous event flow.
9. Add replay / canary runtime evaluation.
10. Run OpenShadow continuously and collect real data.
