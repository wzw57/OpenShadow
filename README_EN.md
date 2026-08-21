# OpenShadow

[中文版](README.md) | **English**

> **Shadow is a personal AI designed to persist and evolve over time.**

OpenShadow is a local-first, runtime-independent platform for personal AI assets and capabilities. The user interacts with one continuous Shadow while runtimes, memory intelligence, databases, search engines, skill systems, providers, voice systems, and other implementations remain replaceable.

The goal is not to rebuild AI infrastructure. OpenShadow keeps a minimal stable core and composes strong external projects through versioned adapters.

## Product model

~~~text
Shadow
├─ Shadow Core
│  ├─ Domain Contracts
│  ├─ Authority & State Transition
│  ├─ Task Continuity
│  ├─ Extension / Integration Registry
│  └─ Portability & Upgrade
│
├─ Replaceable Components
│  ├─ Runtime
│  ├─ Memory Intelligence
│  ├─ Durable Store
│  ├─ Search / Index
│  ├─ Skill System
│  ├─ Capability Providers
│  └─ Voice / User Interfaces
│
└─ User-owned Assets
   ├─ Tasks / Runs / Checkpoints
   ├─ Canonical Memories
   ├─ Skills
   ├─ Extensions / Integrations
   ├─ Asset Catalog
   ├─ Artifacts
   └─ Policies / Action History
~~~

Shadow is the complete product. Shadow Core is only the smallest part that must remain stable.

## Confirmed principles

### Every request goes through Shadow

Every request creates at least a minimal Run record. Full prompts, outputs, and tool traces are retained according to user policy and durable value. Work that must survive sessions, runtimes, waiting conditions, or long periods becomes a Durable Task.

### Shadow owns assets, continuity, and authority

A runtime, memory engine, database-specific format, or provider must not become the irreplaceable owner of the user's long-term assets.

### Replaceable components own intelligence and execution

Reasoning, planning, memory extraction and consolidation, retrieval, embeddings, graphs, speech processing, device protocols, and provider execution should use replaceable implementations.

### Adapters are first-class architecture

OpenShadow defines Port Contracts, the Adapter SDK, manifests, permissions, version negotiation, health contracts, and contract tests. Concrete adapters and implementations can evolve independently.

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

## External information assets

Shadow does not copy and permanently manage all of the user's external information.

For sources such as Notion, Obsidian, Drive, email, and file systems, the Asset Catalog records what exists, where it is, how to access it, and whether it is available. Shadow reads external content on demand for a task, recall, or background memory consolidation.

The source system remains responsible for the original content. Canonical Memory produced from that content becomes a Shadow-owned asset.

## Capability assets

Users accumulate capabilities as well as information:

~~~text
Capability Assets
├─ Skills
├─ Extensions
├─ Integrations
├─ MCP connections
├─ Provider bindings
├─ Runtime profiles
└─ Configuration / permission metadata
~~~

These assets need stable identities, versions, provenance, configuration, permissions, compatibility, and migration metadata so that they remain reusable when runtimes and devices change.

## Current boundary

OpenShadow does not build database engines, general agent loops, memory intelligence, vector or graph databases, foundation models, speech engines, browser agents, coding agents, or device protocol stacks.

OpenShadow must implement:

- Shadow Domain Contracts;
- the authoritative state commit boundary;
- Task and Run continuity;
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
- [Roadmap](docs/roadmap.md)
- [Architecture Decision Records](docs/adr/README.md)

## Status

**Requirements refinement and Core / External responsibility design.**

The current priority is to freeze complete requirements and the irreducible core before selecting concrete external projects.
