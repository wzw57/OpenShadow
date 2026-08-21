# Stage 4 Contract Baseline

- Status: Accepted — frozen by maintainer decision and merged in the Stage 4 PR
- Scope: Phase 0–1 cross-language contracts; no Stage 5 business implementation
- Normative artifacts: [`contracts/`](../contracts/)

This document is the normative prose companion to the checked-in JSON Schema,
OpenAPI, fixtures, and declarative contract cases. When examples elsewhere in
the repository conflict with this baseline, this document and the versioned
artifacts under `contracts/` take precedence until the conflicting document is
corrected.

## 1. Terminology and scope

The stable control component is called the **Tiny Kernel**. `Tiny Core` and
`Shadow Core` are not alternate component names.

Stage 4 freezes only the contracts needed to implement the Phase 0–1 vertical
slice while preserving the complete target architecture. Phase 2–5 concepts
remain compatible but do not receive speculative field-level schemas.

## 2. Canonical records

Every Canonical Record uses a shared envelope containing stable identity,
record and schema type, ownership, classification, provenance, retention,
generic record state, immutable version, creation time, commit time, and a
typed payload.

`expected_version` is not stored in the Canonical Envelope. It is a mutation
precondition. `created_at` is stable across versions; `committed_at` identifies
the commit time of one immutable version.

The generic `record_state` values are `active`, `logically_deleted`, and
`erased`. Profile lifecycle such as Memory `superseded` or Run `waiting`
belongs to the typed payload. An erased record retains only a non-sensitive
Tombstone. Secrets never enter ordinary Canonical Records.

Stable IDs are opaque strings. The reference implementation may generate
UUIDv7, but callers must not infer time, type, or storage location from an ID.
References to a current Head and references to an exact version are different
types.

## 3. Mutation and commit authority

Commands and Proposals share a `MutationInputEnvelope`, discriminated by
`input_kind`. The input schema and target record schema are distinct:

~~~text
input_type / input_schema_ref
target_record_type / target_schema_ref
~~~

Create omits `expected_version`; update, transition, logical delete, and erase
intent require it. Proposals never gain commit authority and cannot supply
Kernel-generated version or timestamp fields.

Every commit attempt produces a structured `CommitDecision`. Only `accepted`
creates a Canonical Version. `conflict` is distinct from policy or validation
rejection. The accepted decision and resulting versions are persisted
atomically. Rejected Proposals do not become user domain assets.

## 4. Profiles and schemas

Schema references are immutable URIs mapped to checked-in files and SHA-256
digests by `contracts/manifest.json`. Schemas use JSON Schema Draft 2020-12;
the API uses OpenAPI 3.1. References must resolve offline.

Schema versions use SemVer:

- patch changes do not alter validation semantics;
- minor changes add safely ignorable optional fields;
- major changes remove fields, add requirements, narrow validation, change
  state meaning, or extend a closed enum.

Profile major changes require semantic migration. JSON Schema validation alone
does not constitute migration.

A Profile Descriptor declares record contracts, input contracts, lifecycle
contracts, validator requirements, migrations, export rules, and compatibility.
It does not embed Python classes or executable paths. A separate Profile
Registration binds an immutable Descriptor version to a replaceable Validator.

Validators are deterministic, side-effect free, have no Repository write
authority, and return only a validity decision plus structured violations.
They may not silently normalize or replace candidate payloads.

## 5. Adapter and capability model

Adapter implementation description, installed instance, and current health are
separate contracts:

- `AdapterDescriptor` describes implementation, contracts, target kinds,
  capabilities, configuration schema, version, and digest;
- `AdapterRegistration` identifies one installed and configured instance;
- `HealthObservation` is time-bound and becomes `unknown` after expiry.

Descriptor declarations never grant permission. Capability negotiation selects
an exact family contract and resolves every required capability. Unknown
required capabilities make a binding incompatible; unknown optional
capabilities may be ignored but are recorded.

An immutable `ExecutionBinding` captures the selected target kind, adapter,
descriptor digest, contract version, resolved capabilities, authorization
envelope, implementation version, selection source, and health observation.
Attempts always reference an exact Binding snapshot.

A versioned `CapabilityEnvelope` contains the principal, grantee, execution
scope, allowed capabilities, data and resource allowlists, budgets, allowed
side effects, approval references, policy version, validity interval, and
revocation state. Empty allowlists deny access. A successful technical Binding
does not imply authorization.

## 6. Runtime messages and execution truth

The transport-neutral Message Envelope separates envelope and payload schema,
identifies request/response/event role, carries exact contract versions, and
uses structured errors. Isolated Adapters negotiate versions through the Host
Control Protocol (`initialize`, `describe`, `health`, `shutdown`). The Runtime
Family base Port remains `describe`, `execute`, and `events`.

Execution Requests carry exact Run, Attempt, Binding, idempotency, authorized
context, Artifact references, deadline, and an immutable CapabilityEnvelope
snapshot. External Adapters may not dereference arbitrary source references.

Execution events are namespaced, ordered per execution, replayed at least once,
and deduplicated by event ID. A cursor gap is explicit. Progress and deltas are
not Canonical State. A logical terminal event may be delivered more than once
but may occur only once.

When a Runtime requires data, budget, tools, or side effects beyond its
Envelope, it emits `shadow.execution.authorization-required` and stops before
crossing the boundary. Without a declared resume capability, continuation uses
a new Attempt.

Cancellation request is not cancellation truth. `cancellation_unknown` and
`outcome_unknown` are reconcilable states, not permanent terminal states.

The first isolated transport uses UTF-8 NDJSON over stdio. Stdout is protocol
only, stderr is sanitized logging, and large data uses Artifact references.

## 7. Canonical Repository

The stable Repository capability is limited to `get`, `get_version`, `query`,
`history`, `commit_batch`, and `record_decision`. It is not a database product,
search engine, graph, workflow system, or arbitrary query interface.

Commit batches are all-or-nothing. Expected Version comparison occurs in the
write transaction. A conflict requires re-reading and re-validating; callers
must not merely replace the expected version and retry.

Idempotency is scoped and digest-bound. Reusing a scope and key with a different
request digest is an idempotency conflict. If a response is lost after the
Store may have committed, the caller retries with the same key to discover the
original result.

Logical deletion is a normal new version. Physical erasure uses a separate
Erasure operation and leaves a minimal Tombstone. Store outage pauses Canonical
Commit and denies real-world side effects by default. In-memory work is never
silently backfilled as canonical history.

## 8. Admission, Request, Run, and API

Only work-bearing finalized inputs enter Admission. Health, read-only queries,
existing Run subscriptions, and internal recovery do not create Requests or
Runs.

An accepted Conversation turn atomically creates an Admission Record, immutable
User Message, new Conversation Version, immutable Request, Execution
Requirements, and exactly one Root Run. An idempotent replay returns the
original result and does not create another Admission Record.

Requirements describe what work needs; CapabilityEnvelope describes what is
authorized; ExecutionBinding describes what was selected. They remain separate.

Run terminal states are `completed`, `failed`, and `cancelled`.
`cancellation_unknown` can later reconcile to a truthful terminal state.
Attempt timeouts that cannot prove the Target stopped become `outcome_unknown`.

Store-outage interaction is named `EphemeralExecution`, not Ephemeral Run. It
has no Canonical Run ID, cannot create durable assets or side effects, and is
never silently converted to history.

The Phase 0–1 API surface is defined by `contracts/openapi/openapi.yaml` and
includes Conversation creation and turns, Message listing, Admission/Request
lookup, Run snapshot/events/cancel, Memory control, Proposal decisions, and
health/readiness.

## 9. Conversation and Memory Profiles

Message is an immutable record. Conversation stores ordered Message references
and one foreground Run reference. Runtime deltas remain transient; only final
Shadow-approved output becomes an Assistant Message.

While a foreground Run is active, Phase 0–1 supports `queue-next` and
`cancel-and-replace`. It does not support silently modifying the current
Request. Live input requires a future explicit Runtime capability and ADR.

Memory uses the Canonical Envelope version directly. There is no parallel
`MemoryVersion` entity or second current-version pointer. Corrections create a
new version of the same Memory ID; cross-Memory merges atomically create a new
Memory and supersede the input Memories.

Canonical Memory stores typed content, applicability scope, Evidence and source
references, source dependency, lifecycle, supersede relationships, and origin.
Embedding, graph, rank, confidence, and recall score are derived by default.
Ordinary responses never automatically become Memory.

Memory Intelligence submits typed proposals. A pending proposal may be stored
as a restricted control record when review must survive restart, but it is not
Canonical Memory until accepted.

Every correction, invalidation, or merge target pairs its Stable Record
reference with its own Expected Version. Separate parallel target and version
arrays are not a valid proposal representation.

## 10. Agent Skills compatibility

The official Skill Profile preserves an Agent Skills bundle without injecting
Shadow fields. `SKILL.md` remains required; other files and directories are
allowed by the external specification. Shadow governance is a separate
SkillAsset sidecar bound to an immutable snapshot or pinned revision and a
deterministic bundle digest.

Experimental `allowed-tools` is a hint only and never grants a Shadow
Capability. Trust and high-risk authorization are bound to the exact bundle
digest and are invalidated by content changes.

The digest manifest sorts normalized relative paths and hashes raw file bytes.
It ignores timestamps, ownership, archive ordering, and executable bits.
Absolute paths, traversal, and symlinks are rejected by the reference import
policy.

## 11. Stage 4 exit gate

Stage 4 can be accepted only when:

1. all checked-in schemas parse and all references resolve offline;
2. valid and invalid fixtures behave as declared;
3. OpenAPI 3.1 validates against the same schemas;
4. declarative Contract Test cases cover Kernel, Profiles, Adapters, Runtime,
   Repository, API, portability, and Agent Skills;
5. documentation uses Tiny Kernel consistently and contains no known semantic
   contradiction with this baseline;
6. PR review is complete and the branch is merged.

The Stage 4 ADRs and the reference implementation profile are now `Accepted`.
Changes to these boundaries require a new ADR or a versioned contract update.
