from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .commit import CommitAuthority
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


class AdmissionService:
    def __init__(self, repository: CanonicalRepository, authority: CommitAuthority):
        self.repository = repository
        self.authority = authority

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
    ) -> AdmissionResult:
        required_capabilities = required_capabilities or []
        acceptable_target_kinds = acceptable_target_kinds or ["shadow.deterministic-runner"]
        correlation_id = correlation_id or new_id("correlation")
        submitted_at = utc_timestamp()
        submission_id = new_id("submission")
        request_digest = sha256_digest(
            {
                "request_type": request_type,
                "input_type": input_type,
                "work_input": work_input.model_dump(mode="json")
                if isinstance(work_input, RecordVersionRef)
                else work_input,
                "principal_ref": principal_ref,
                "endpoint_ref": endpoint_ref,
                "space_id": space_id,
            }
        )

        if not self.repository.available:
            return AdmissionResult(
                decision="ephemeral",
                ephemeral=EphemeralExecution(
                    execution_id=new_id("ephemeral"),
                    message="Canonical Repository is unavailable; no durable state was created.",
                ),
            )

        admission_id = new_id("admission")
        request_id = new_id("request")
        requirements_id = new_id("requirements")
        run_id = new_id("run")
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
            lifecycle="queued",
            requirements_ref=RecordVersionRef(record_id=requirements_id, version=1),
        )
        provenance = Provenance(origin_type="shadow.origin.user-command", origin_ref=submission_id)
        operations = [
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
                typed_payload=admission_payload.model_dump(mode="json"),
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
                typed_payload=requirements_payload.model_dump(mode="json"),
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
                typed_payload=request_payload.model_dump(mode="json"),
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
                typed_payload=run_payload.model_dump(mode="json"),
            ),
        ]
        plan = CommitPlan(
            commit_request_id=new_id("commit-request"),
            idempotency_scope=f"admission:{principal_ref}:{space_id}",
            idempotency_key=idempotency_key or submission_id,
            request_digest=request_digest,
            actor_ref=principal_ref,
            operations=operations,
            prepared_at=submitted_at,
            correlation_id=correlation_id,
        )
        self.authority.commit(plan)
        return AdmissionResult(
            decision="accepted",
            admission=self.repository.get(admission_id),
            request=self.repository.get(request_id),
            requirements=self.repository.get(requirements_id),
            run=self.repository.get(run_id),
        )
