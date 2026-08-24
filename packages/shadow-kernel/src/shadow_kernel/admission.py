from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .commit import CommitAuthority
from .errors import ShadowDomainError, ShadowError
from .ids import new_id, sha256_digest, utc_timestamp
from .models import (
    AdmissionRecordPayload,
    CommitOperation,
    CommitPlan,
    EphemeralExecution,
    ExecutionRequirementsPayload,
    Provenance,
    RecordVersionRef,
    RequestPayload,
    RunPayload,
    StableRecordRef,
)
from .repository import CanonicalRepository

KERNEL_SCHEMA = "https://schemas.openshadow.dev/contracts/kernel/1.0.0"
RETENTION_REF = StableRecordRef(record_id="retention-default")


@dataclass(slots=True)
class AdmissionResult:
    decision: str
    admission: dict[str, Any] | None = None
    request: dict[str, Any] | None = None
    requirements: dict[str, Any] | None = None
    run: dict[str, Any] | None = None
    ephemeral: EphemeralExecution | None = None
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class AdmissionPreparation:
    """The Admission-owned core records and operations before an atomic commit."""

    admission: AdmissionRecordPayload
    request: RequestPayload
    requirements: ExecutionRequirementsPayload
    run: RunPayload
    operations: tuple[CommitOperation, ...]
    submission_id: str
    request_digest: str
    idempotency_scope: str
    idempotency_key: str
    principal_ref: str
    prepared_at: str
    correlation_id: str


class AdmissionService:
    def __init__(self, repository: CanonicalRepository, authority: CommitAuthority):
        self.repository = repository
        self.authority = authority

    def prepare(
        self,
        *,
        request_type: str,
        input_type: str,
        work_input: RecordVersionRef | dict[str, Any],
        principal_ref: str,
        endpoint_ref: str,
        space_id: str,
        required_capabilities: list[str] | None = None,
        acceptable_target_kinds: list[str] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        submission_id: str | None = None,
        request_digest: str | None = None,
        idempotency_scope: str | None = None,
        record_ids: dict[str, str] | None = None,
        run_lifecycle: str = "queued",
        run_binding_refs: list[RecordVersionRef] | None = None,
        run_attempt_refs: list[RecordVersionRef] | None = None,
        run_active_attempt_ref: StableRecordRef | None = None,
        run_started_at: str | None = None,
    ) -> AdmissionPreparation:
        """Construct only Admission records; callers own any larger atomic CommitPlan."""
        required_capabilities = required_capabilities or []
        acceptable_target_kinds = acceptable_target_kinds or ["shadow.deterministic-runner"]
        correlation_id = correlation_id or new_id("correlation")
        submitted_at = utc_timestamp()
        submission_id = submission_id or new_id("submission")
        provided_ids = record_ids or {}
        computed_request_digest = sha256_digest(
            {
                "request_type": request_type,
                "input_type": input_type,
                "work_input": work_input.model_dump(mode="json", exclude_none=True)
                if isinstance(work_input, RecordVersionRef)
                else work_input,
                "principal_ref": principal_ref,
                "endpoint_ref": endpoint_ref,
                "space_id": space_id,
            }
        )
        request_digest = request_digest or computed_request_digest
        idempotency_key = idempotency_key or submission_id
        idempotency_scope = idempotency_scope or f"admission:{principal_ref}:{space_id}"

        admission_id = provided_ids.get("admission_id") or new_id("admission")
        request_id = provided_ids.get("request_id") or new_id("request")
        requirements_id = provided_ids.get("requirements_id") or new_id("requirements")
        run_id = provided_ids.get("run_id") or new_id("run")
        now = utc_timestamp()
        admission_payload = AdmissionRecordPayload(
            admission_id=admission_id,
            submission_id=submission_id,
            input_type=input_type,
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            space_id=space_id,
            request_digest=request_digest,
            decision="accepted",
            request_ref=StableRecordRef(record_id=request_id),
            root_run_ref=StableRecordRef(record_id=run_id),
            decided_at=now,
            retention_policy_ref=RETENTION_REF,
        )
        requirements_payload = ExecutionRequirementsPayload(
            requirements_id=requirements_id,
            required_capabilities=required_capabilities,
            acceptable_target_kinds=acceptable_target_kinds,
            allowed_side_effects=[],
            streaming_required=True,
            checkpoint_required=False,
            created_from=RecordVersionRef(record_id=admission_id, version=1),
        )
        request_payload = RequestPayload(
            admission_ref=RecordVersionRef(record_id=admission_id, version=1),
            request_type=request_type,
            work_input=work_input,
            requirements_ref=RecordVersionRef(record_id=requirements_id, version=1),
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            accepted_at=now,
            correlation_id=correlation_id,
        )
        run_payload = RunPayload(
            request_ref=RecordVersionRef(record_id=request_id, version=1),
            lifecycle=run_lifecycle,
            requirements_ref=RecordVersionRef(record_id=requirements_id, version=1),
            binding_refs=run_binding_refs or [],
            attempt_refs=run_attempt_refs or [],
            active_attempt_ref=run_active_attempt_ref,
            started_at=run_started_at,
        )
        provenance = Provenance(origin_type="shadow.origin.user-command", origin_ref=submission_id)
        operations = (
            CommitOperation(
                operation_id=new_id("operation"),
                operation="create",
                record_id=admission_id,
                record_type="shadow.kernel.admission",
                target_schema_ref=f"{KERNEL_SCHEMA}#/$defs/AdmissionRecordPayload",
                owner_ref=principal_ref,
                space_id=space_id,
                created_by=principal_ref,
                data_classification="personal",
                provenance=provenance,
                retention_policy_ref=RETENTION_REF,
                typed_payload=admission_payload.model_dump(mode="json", exclude_none=True),
            ),
            CommitOperation(
                operation_id=new_id("operation"),
                operation="create",
                record_id=requirements_id,
                record_type="shadow.kernel.execution-requirements",
                target_schema_ref=f"{KERNEL_SCHEMA}#/$defs/ExecutionRequirementsPayload",
                owner_ref=principal_ref,
                space_id=space_id,
                created_by=principal_ref,
                data_classification="personal",
                provenance=provenance,
                retention_policy_ref=RETENTION_REF,
                typed_payload=requirements_payload.model_dump(mode="json", exclude_none=True),
            ),
            CommitOperation(
                operation_id=new_id("operation"),
                operation="create",
                record_id=request_id,
                record_type="shadow.kernel.request",
                target_schema_ref=f"{KERNEL_SCHEMA}#/$defs/RequestPayload",
                owner_ref=principal_ref,
                space_id=space_id,
                created_by=principal_ref,
                data_classification="personal",
                provenance=provenance,
                retention_policy_ref=RETENTION_REF,
                typed_payload=request_payload.model_dump(mode="json", exclude_none=True),
            ),
            CommitOperation(
                operation_id=new_id("operation"),
                operation="create",
                record_id=run_id,
                record_type="shadow.kernel.run",
                target_schema_ref=f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                owner_ref=principal_ref,
                space_id=space_id,
                created_by=principal_ref,
                data_classification="personal",
                provenance=provenance,
                retention_policy_ref=RETENTION_REF,
                typed_payload=run_payload.model_dump(mode="json", exclude_none=True),
            ),
        )
        return AdmissionPreparation(
            admission=admission_payload,
            request=request_payload,
            requirements=requirements_payload,
            run=run_payload,
            operations=operations,
            submission_id=submission_id,
            request_digest=request_digest,
            idempotency_scope=idempotency_scope,
            idempotency_key=idempotency_key,
            principal_ref=principal_ref,
            prepared_at=submitted_at,
            correlation_id=correlation_id,
        )

    def admit(
        self,
        *,
        request_type: str,
        input_type: str,
        work_input: RecordVersionRef | dict[str, Any],
        principal_ref: str,
        endpoint_ref: str,
        space_id: str,
        required_capabilities: list[str] | None = None,
        acceptable_target_kinds: list[str] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        submission_id: str | None = None,
        request_digest: str | None = None,
        idempotency_scope: str | None = None,
        record_ids: dict[str, str] | None = None,
        run_lifecycle: str = "queued",
        run_binding_refs: list[RecordVersionRef] | None = None,
        run_attempt_refs: list[RecordVersionRef] | None = None,
        run_active_attempt_ref: StableRecordRef | None = None,
        run_started_at: str | None = None,
    ) -> AdmissionResult:
        if not self.repository.available:
            return AdmissionResult(
                decision="ephemeral",
                ephemeral=EphemeralExecution(
                    execution_id=new_id("ephemeral"),
                    message="Canonical Repository is unavailable; no durable state was created.",
                ),
            )
        if (
            isinstance(work_input, RecordVersionRef)
            and self.repository.get(work_input.record_id, work_input.version) is None
        ):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.admission.work-input-not-found",
                    category="validation",
                    message="A durable work input reference must resolve before admission.",
                    typed_details=work_input.model_dump(mode="json"),
                )
            )

        preparation = self.prepare(
            request_type=request_type,
            input_type=input_type,
            work_input=work_input,
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            space_id=space_id,
            required_capabilities=required_capabilities,
            acceptable_target_kinds=acceptable_target_kinds,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            submission_id=submission_id,
            request_digest=request_digest,
            idempotency_scope=idempotency_scope,
            record_ids=record_ids,
            run_lifecycle=run_lifecycle,
            run_binding_refs=run_binding_refs,
            run_attempt_refs=run_attempt_refs,
            run_active_attempt_ref=run_active_attempt_ref,
            run_started_at=run_started_at,
        )
        plan = CommitPlan(
            commit_request_id=new_id("commit-request"),
            idempotency_scope=preparation.idempotency_scope,
            idempotency_key=preparation.idempotency_key,
            request_digest=preparation.request_digest,
            actor_ref=preparation.principal_ref,
            operations=list(preparation.operations),
            prepared_at=preparation.prepared_at,
            correlation_id=preparation.correlation_id,
        )
        result = self.authority.commit(plan)
        if result.outcome in {"failed", "conflict"}:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.admission.commit-failed",
                    category="conflict" if result.outcome == "conflict" else "validation",
                    message="Admission lifecycle could not be committed.",
                    typed_details=result.structured_error,
                )
            )
        return AdmissionResult(
            decision="accepted",
            admission=self.repository.get(preparation.admission.admission_id),
            request=self.repository.get(preparation.request.admission_ref.record_id),
            requirements=self.repository.get(preparation.requirements.requirements_id),
            run=self.repository.get(preparation.admission.root_run_ref.record_id),
            replayed=result.outcome == "idempotent_replay",
        )
