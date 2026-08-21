# OpenShadow

[中文版](README.md) | **English**

> **Shadow is a personal AI designed to persist and evolve over time.**

OpenShadow is a local-first, implementation-independent platform for personal AI assets and capabilities. The user interacts with one continuous Shadow while agent runtimes, models, memory intelligence, routers, runners, databases, voice systems, devices, and other fast-moving implementations remain replaceable.

Shadow does not rebuild the AI ecosystem. It combines external projects behind a small sovereignty kernel while preserving the identity, memory, work, capabilities, and governance records accumulated by the user.

## Product structure

~~~text
Shadow
├─ Tiny Kernel
│  ├─ Identity & Ownership
│  ├─ Canonical Record & Lifecycle
│  ├─ Proposal / Validate / Commit Authority
│  ├─ Work Admission & Minimal Continuity
│  ├─ Extension Contract & Binding
│  └─ Portability & Erasure Intent
│
├─ Official Profiles
│  ├─ Conversation / Memory / State
│  ├─ Durable Task / Action
│  ├─ Skill / Capability / Integration
│  └─ Profile-specific schemas and invariants
│
├─ Replaceable Components
│  ├─ Runtime / Model / Runner / Workflow / Router
│  ├─ Memory Intelligence / Retrieval / State Resolver
│  ├─ Store / Search / Scheduler / Policy Engine
│  ├─ Source / Provider / MCP / Skill Runtime
│  └─ Web / Voice / Device Interfaces
│
└─ User-owned Assets
   ├─ Conversations / Memories / Tasks / State
   ├─ Skills / Executables / Integrations
   ├─ External Asset Catalog / Artifacts
   └─ Bindings / Policies / Action History
~~~

Shadow is the complete product. Tiny Kernel understands only control semantics required for sovereignty and continuity. Memory, state, task, and skill semantics are versioned Profiles rather than permanent kernel modules.

## Core invariants

### All work-bearing input goes through Shadow

Chat, voice, schedules, events, API commands, and Semantic Pulse proposals pass through Admission. Each accepted work Request creates one Root Run; rejected admission creates only a minimal Admission Record.

Health checks, static assets, read-only control-plane queries, subscriptions to an existing Run, and internal recovery steps do not create a Root Run, although identity, policy, and audit still apply.

### All execution is governed by Shadow, but not all work uses an Agent Runtime

Execution Binding uses an extensible, namespaced `target_kind`. Initial well-known kinds are:

- `shadow.agent-runtime`;
- `shadow.model-worker`;
- `shadow.deterministic-runner`;
- `shadow.workflow-target`;
- `shadow.capability-provider`.

They are not a permanently closed enum. Core governs capabilities, data boundaries, side effects, budgets, and health instead of hard-coding each target kind.

### External intelligence proposes; Shadow commits

~~~text
External Intelligence / Execution
                ↓
          Typed Proposal
                ↓
   Schema + Authority + Policy Validation
                ↓
        Canonical Commit
                ↓
  Versioned Canonical Record / Profile
~~~

A memory engine cannot directly change memory, a router cannot change a binding, a runtime cannot complete a durable task, a state resolver cannot change accepted state, and a provider cannot bypass the action boundary.

### Canonical records share governance without becoming arbitrary JSON

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ classification / provenance
├─ version / lifecycle / retention
└─ typed_payload
~~~

The envelope provides identity, ownership, versioning, provenance, and lifecycle. Each Profile still defines typed schemas, valid transitions, and migration rules. Syntactic schema replacement is not a substitute for semantic migration.

## Memory and state

Canonical Memory is a user-owned `memory` Profile and survives replacement of memory intelligence. External components perform extraction, consolidation, recall, deduplication, embedding, graph construction, and ranking; Shadow governs candidates, versions, provenance, correction, erasure, and commit.

World State is an official `state` Profile, not a knowledge graph embedded in Tiny Kernel. Kernel provides identity, provenance, evidence, temporal validity, and commit. The Profile defines state keys, Observations, fresh / stale / unknown, and migrations. Collection, fusion, prediction, ontologies, and domain queries remain external.

Accepted state is portable and recoverable but may expire. Shadow refreshes external sources when needed and explicitly represents stale or unknown information.

## Skills and capability assets

Shadow does not invent a Skill content format. The official Profile is natively compatible with the [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx), preserving standard `SKILL.md` bundles and optional `scripts/`, `references/`, and `assets/`.

A Shadow `SkillAsset` stores governance only: stable ID, Owner / Space, source, pinned revision, digest, trust, permission policy, classification, installation state, and Runtime projections. Shadow metadata does not mutate the standard bundle, and provider Skill IDs remain external references.

Discovery, loading, prompt projection, script execution, and provider upload belong to adapters. Shadow independently enforces trust and permissions and does not treat experimental `allowed-tools` metadata as final authority.

External information follows the same principle. Original Notion, Obsidian, Drive, email, and filesystem content remains in its source; Shadow normally records what exists, where it is, and how to access it.

## Adapter and infrastructure boundary

The common `AdapterDescriptor` remains minimal:

~~~text
adapter_id
adapter_family
contract_versions
capabilities
config_schema_ref
implementation_ref
health
~~~

Permissions, secrets, migrations, checkpoints, data boundaries, and reconciliation are family-specific optional capabilities.

The base Runtime Port requires only `describe`, `execute`, and `events`. Cancellation, checkpoints, native resume, semantic handoff, progress, usage, and reconciliation are negotiated capabilities. Adapters must not emulate unsupported behavior.

Shadow does not abstract an entire database. Store capabilities are separated into Canonical Repository, Migration, Portable Export / Import, Backup, Outbox, and Integrity. Only canonical semantics and standard portable export require cross-store consistency.

## Governance and long-term evolution

- Every Canonical Record has explicit Owner and Space from the first version.
- Near-term delivery remains single-user with a default Personal Space and implicit Home Space.
- Core enforces only small deterministic policy primitives: data class, capability, approval, budget, side effect, expiry, and revocation.
- Complex policy evaluation may be external; Core retains final enforcement.
- Users retain correction, logical deletion, final physical erasure, export, and migration rights.
- Standard export excludes secrets, caches, indexes, and implementation-private state.
- Store failure pauses Canonical Commit and blocks unrecorded real-world side effects by default.
- Domain Events are notification envelopes, not mandatory event sourcing.
- Outbox is limited to reliable cross-boundary side effects.
- OperationJob is limited to migration, export, backup, and erasure.

## Explicit non-goals

OpenShadow does not build database engines, general agent loops, foundation models, intelligent routing algorithms, memory intelligence, vector or graph databases, workflow engines, script runtimes and sandboxes, speech engines, browser or coding agents, device protocol stacks, or domain digital twins.

OpenShadow implements:

- Stable ID, Owner, Space, Version, and Canonical Envelope;
- Proposal / Validate / Commit authority;
- Admission, Run / Attempt, and minimal Task continuity;
- Profile registration, schema compatibility, and migration control;
- a minimal Adapter Registry, Binding, and capability validation;
- deterministic data, authorization, budget, and side-effect enforcement;
- standard export, integrity verification, and Erasure Intent;
- user APIs for inspection, correction, revocation, deletion, and export.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Core / External Responsibility Matrix](docs/responsibility-matrix.md)
- [Key Use Cases](docs/use-cases/README.md)
- [Domain Model](docs/domain-model.md)
- [State Machine Baseline](docs/state-machines.md)
- [Complete Technical Architecture](docs/technical-architecture.md)
- [Phased Implementation Plan](docs/implementation-stages.md)
- [Reference Implementation Profile](docs/implementation-profile.md)
- [Roadmap](docs/roadmap.md)
- [Stage 4 Contract Baseline](docs/contract-baseline.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

Stages 0–3 established the requirements, responsibility, use-case, and domain baselines. Stage 4 decisions D1–D8 are frozen and now have field-level schemas, OpenAPI, fixtures, and declarative Contract Tests. The work remains Proposed until final PR review and merge are complete.
