# Architecture Decision Records (ADR)

OpenShadow is intended to live for years while models, Agent runtimes, memory engines and provider ecosystems change. Important architectural decisions therefore need a durable record of **what was decided, why, what alternatives were rejected, and what would justify revisiting the decision**.

This directory stores Architecture Decision Records.

## ADR format

Create files using:

```text
NNNN-short-title.md
```

Example:

```text
0001-shadow-owns-durable-state.md
0002-postgresql-as-v0-1-source-of-truth.md
0003-runtime-handoff-uses-semantic-checkpoints.md
```

Recommended template:

```md
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded | Deprecated
- Date: YYYY-MM-DD
- Owners: ...

## Context

What problem forced this decision?

## Decision

What are we doing?

## Rationale

Why this option?

## Alternatives considered

What else was considered and why was it rejected?

## Consequences

Positive and negative consequences.

## Revisit triggers

What future evidence or technology change should cause this decision to be reconsidered?
```

## Initial decisions to record

The following decisions are currently part of the v0.3 implementation baseline and should receive dedicated ADRs as implementation begins:

1. **Shadow owns durable continuity; Runtime does not.**
2. **Task belongs to Shadow and Runtime only executes it.**
3. **Runtime handoff uses Semantic Checkpoint rather than hidden/internal reasoning state migration.**
4. **Raw Evidence is the durable evidence layer; Canonical Memory is a revisable interpretation.**
5. **Derived indexes are disposable and rebuildable.**
6. **Memory retrieval is task-aware and MemoryNeed-driven rather than default vector top-k.**
7. **All meaningful side effects pass through Capability Gateway and Execution Ledger.**
8. **PostgreSQL is the V0.1 source of truth.**
9. **V0.1 uses a modular monolith rather than microservices.**
10. **Existing Agent / Memory / Home / Coding systems are reused unless continuity requires Shadow ownership.**

## Core philosophy

> **Shadow owns the continuity.**

An ADR should be added whenever a decision changes the stable boundary between Shadow and a replaceable Runtime, Memory Engine, Capability Provider, interaction client, or storage component.
