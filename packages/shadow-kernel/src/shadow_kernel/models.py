from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class StableRecordRef(StrictModel):
    record_id: str = Field(min_length=1, max_length=128)


class RecordVersionRef(StableRecordRef):
    version: int = Field(ge=1)


class Provenance(StrictModel):
    origin_type: str = Field(min_length=1, max_length=200)
    origin_ref: str = Field(min_length=1, max_length=1000)
    source_refs: list[StableRecordRef] = Field(default_factory=list)
    extensions: dict[str, Any] | None = None


class CanonicalEnvelope(StrictModel):
    record_id: str
    record_type: str
    schema_ref: str
    owner_ref: str
    space_id: str
    created_by: str
    data_classification: Literal["public", "personal", "sensitive", "restricted"]
    provenance: Provenance
    version: int = Field(ge=1)
    retention_policy_ref: StableRecordRef
    record_state: Literal["active", "logically_deleted", "erased"] = "active"
    created_at: str
    committed_at: str
    typed_payload: Any
    extensions: dict[str, Any] | None = None


class MutationInputEnvelope(StrictModel):
    input_id: str
    input_kind: Literal["command", "proposal"]
    input_type: str
    input_schema_ref: str
    operation: Literal["create", "update", "transition", "logical_delete", "erase"]
    submitted_by: str
    target_record_type: str
    target_schema_ref: str
    idempotency_key: str
    submitted_at: str
    typed_payload: Any
    target_record_id: str | None = None
    expected_version: int | None = Field(default=None, ge=1)
    correlation_id: str | None = None
    causation_id: str | None = None
    valid_until: str | None = None
    extensions: dict[str, Any] | None = None


class CommitOperation(StrictModel):
    operation_id: str
    operation: Literal["create", "update", "transition", "logical_delete", "erase"]
    record_id: str
    record_type: str
    target_schema_ref: str
    owner_ref: str
    space_id: str
    created_by: str
    data_classification: Literal["public", "personal", "sensitive", "restricted"]
    provenance: Provenance
    retention_policy_ref: StableRecordRef
    record_state: Literal["active", "logically_deleted", "erased"] = "active"
    typed_payload: Any
    expected_version: int | None = Field(default=None, ge=1)


class CommitPlan(StrictModel):
    commit_request_id: str
    idempotency_scope: str
    idempotency_key: str
    request_digest: str
    actor_ref: str
    operations: list[CommitOperation] = Field(min_length=1)
    prepared_at: str
    correlation_id: str | None = None
    causation_id: str | None = None


class OperationResult(StrictModel):
    operation_id: str
    record_id: str
    previous_version: int | None = None
    resulting_version: int | None = None
    conflict_current_version: int | None = None


class CommitBatchResult(StrictModel):
    outcome: Literal["committed", "conflict", "idempotent_replay", "failed"]
    operation_results: list[OperationResult]
    commit_id: str | None = None
    repository_revision: str | None = None
    committed_at: str | None = None
    structured_error: dict[str, Any] | None = None


class CommitDecision(StrictModel):
    commit_id: str
    input_id: str
    decision: Literal["accepted", "rejected", "conflict"]
    target_record_id: str
    decided_at: str
    previous_version: int | None = None
    resulting_version: int | None = None
    reason_code: str | None = None
    reason_detail: str | None = None


class AdmissionRecordPayload(StrictModel):
    admission_id: str
    submission_id: str
    input_type: str
    request_digest: str
    decision: Literal["accepted", "rejected", "approval_required"]
    decided_at: str
    retention_policy_ref: StableRecordRef
    principal_ref: str | None = None
    endpoint_ref: str | None = None
    space_id: str | None = None
    public_reason_code: str | None = None
    restricted_detail_ref: StableRecordRef | None = None
    request_ref: StableRecordRef | None = None
    root_run_ref: StableRecordRef | None = None
    approval_request_ref: StableRecordRef | None = None


class RequestPayload(StrictModel):
    admission_ref: RecordVersionRef
    request_type: str
    work_input: RecordVersionRef | dict[str, Any]
    requirements_ref: RecordVersionRef
    principal_ref: str
    endpoint_ref: str
    accepted_at: str
    correlation_id: str
    deadline: str | None = None


class ExecutionRequirementsPayload(StrictModel):
    requirements_id: str
    required_capabilities: list[str]
    acceptable_target_kinds: list[str] = Field(min_length=1)
    allowed_side_effects: list[str] = Field(default_factory=list)
    streaming_required: bool = False
    checkpoint_required: bool = False
    created_from: RecordVersionRef
    data_requirements: dict[str, Any] | None = None
    resource_requirements: dict[str, Any] | None = None
    budget_ceiling: list[dict[str, Any]] | None = None
    deadline: str | None = None


class RunPayload(StrictModel):
    request_ref: RecordVersionRef
    lifecycle: Literal[
        "created",
        "queued",
        "running",
        "waiting",
        "paused",
        "cancelling",
        "cancellation_unknown",
        "completed",
        "failed",
        "cancelled",
    ]
    requirements_ref: RecordVersionRef
    binding_refs: list[RecordVersionRef] = Field(default_factory=list)
    attempt_refs: list[RecordVersionRef] = Field(default_factory=list)
    active_attempt_ref: StableRecordRef | None = None
    result_ref: RecordVersionRef | None = None
    failure_summary: dict[str, Any] | None = None
    usage_summary: dict[str, Any] | None = None
    cancellation_request_ref: StableRecordRef | None = None
    started_at: str | None = None
    terminal_at: str | None = None
    last_event_cursor: str | None = None


class ExecutionAttemptPayload(StrictModel):
    run_ref: StableRecordRef
    binding_ref: RecordVersionRef
    lifecycle: Literal[
        "created",
        "dispatching",
        "running",
        "cancellation_requested",
        "succeeded",
        "failed",
        "cancelled",
        "rejected",
        "incompatible",
        "outcome_unknown",
    ]
    attempt_number: int = Field(ge=1)
    execution_ref: str | None = None
    result_ref: RecordVersionRef | None = None
    failure_summary: dict[str, Any] | None = None
    started_at: str | None = None
    finished_at: str | None = None


class ContentBlock(StrictModel):
    block_type: str
    content_schema_ref: str
    typed_content: Any | None = None
    artifact_ref: RecordVersionRef | None = None


class ConversationPayload(StrictModel):
    conversation_state: Literal["open", "archived"]
    message_refs: list[RecordVersionRef] = Field(default_factory=list)
    queued_run_refs: list[StableRecordRef] = Field(default_factory=list)
    title: str | None = None
    foreground_run_ref: StableRecordRef | None = None
    profile_settings: dict[str, Any] | None = None


class MessagePayload(StrictModel):
    conversation_ref: StableRecordRef
    sequence: int = Field(ge=1)
    message_type: str
    author_ref: str
    content_blocks: list[ContentBlock] = Field(min_length=1)
    finalized_at: str
    reply_to: RecordVersionRef | None = None
    source_request_ref: RecordVersionRef | None = None
    produced_by_run_ref: RecordVersionRef | None = None


class EphemeralExecution(StrictModel):
    execution_id: str
    state: Literal["ephemeral"] = "ephemeral"
    durable: Literal[False] = False
    message: str
