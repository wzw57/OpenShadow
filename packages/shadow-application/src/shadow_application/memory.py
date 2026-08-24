from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    Provenance,
    StableRecordRef,
)
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

PROFILE_SCHEMA = "https://schemas.openshadow.dev/contracts/profiles/1.0.0"
RETENTION_REF = StableRecordRef(record_id="retention-default")


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    candidate_id: str
    submitted_by: str
    owner_ref: str
    space_id: str
    payload: dict[str, Any]


class MemoryService:
    """Candidate -> Commit boundary for user-authored Memory lifecycle operations."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def propose_create(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        memory_kind: str,
        content_schema_ref: str,
        typed_content: Any,
        applicability_scope: dict[str, Any],
        evidence_refs: list[dict[str, Any]] | None = None,
        source_refs: list[str] | None = None,
        source_dependency: str = "independent",
    ) -> MemoryCandidate:
        candidate_id = f"memory-candidate-{sha256_digest({'owner': owner_ref, 'space': space_id, 'content': typed_content})[7:31]}"
        proposal = {
            "proposed_operation": "create",
            "targets": [],
            "memory_kind": memory_kind,
            "content_schema_ref": content_schema_ref,
            "proposed_content": typed_content,
            "applicability_scope": applicability_scope,
            "evidence_refs": evidence_refs or [],
            "source_refs": source_refs or [],
            "source_dependency": source_dependency,
        }
        try:
            self.registry.validate(proposal, f"{PROFILE_SCHEMA}#/$defs/MemoryProposalPayload")
        except JsonSchemaValidationError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.candidate-invalid",
                    category="validation",
                    message="Memory Candidate does not satisfy the Memory Profile contract.",
                    typed_details={"path": list(exc.absolute_path), "detail": exc.message},
                )
            ) from exc
        return MemoryCandidate(candidate_id, submitted_by, owner_ref, space_id, proposal)

    def commit_candidate(
        self, candidate: MemoryCandidate, *, idempotency_key: str
    ) -> dict[str, Any]:
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable; Memory was not committed.",
                    retryable=True,
                )
            )
        memory_id = f"memory-{sha256_digest({'candidate': candidate.candidate_id, 'key': idempotency_key})[7:31]}"
        proposal = candidate.payload
        payload = {
            "memory_kind": proposal["memory_kind"],
            "content_schema_ref": proposal["content_schema_ref"],
            "typed_content": proposal["proposed_content"],
            "applicability_scope": proposal["applicability_scope"],
            "evidence_refs": proposal["evidence_refs"],
            "source_refs": proposal["source_refs"],
            "source_dependency": proposal["source_dependency"],
            "memory_state": "active",
            "supersedes_memory_refs": [],
            "created_from_ref": {"record_id": candidate.candidate_id},
        }
        provenance = Provenance(
            origin_type="shadow.origin.user-command", origin_ref=candidate.candidate_id
        )
        operation = CommitOperation(
            operation_id=f"operation-{memory_id}",
            operation="create",
            record_id=memory_id,
            record_type="shadow.profile.memory",
            target_schema_ref=f"{PROFILE_SCHEMA}#/$defs/MemoryPayload",
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            created_by=candidate.submitted_by,
            data_classification="personal",
            provenance=provenance,
            retention_policy_ref=RETENTION_REF,
            typed_payload=payload,
        )
        plan = CommitPlan(
            commit_request_id=f"commit-request-{memory_id}",
            idempotency_scope=f"memory:{candidate.owner_ref}:{candidate.space_id}",
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(candidate.payload),
            actor_ref=candidate.submitted_by,
            operations=[operation],
            prepared_at=utc_timestamp(),
        )
        result = self.authority.commit(plan)
        if result.outcome in {"conflict", "failed"}:
            category = "conflict" if result.outcome == "conflict" else "validation"
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.commit-failed",
                    category=category,
                    message="Memory Candidate could not be committed.",
                    typed_details=result.model_dump(mode="json", exclude_none=True),
                )
            )
        record = self.repository.get(memory_id)
        if record is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.record-missing",
                    category="internal",
                    message="Committed Memory could not be read back.",
                )
            )
        return record

    def propose_correction(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        memory_id: str,
        expected_version: int,
        memory_kind: str,
        content_schema_ref: str,
        typed_content: Any,
        applicability_scope: dict[str, Any],
        evidence_refs: list[dict[str, Any]] | None = None,
        source_refs: list[str] | None = None,
        source_dependency: str = "independent",
    ) -> MemoryCandidate:
        target = self._target_ref(memory_id, expected_version)
        self._load_target(
            memory_id,
            expected_version,
            owner_ref=owner_ref,
            space_id=space_id,
            allow_stale=False,
        )
        proposal = {
            "proposed_operation": "correct",
            "targets": [target],
            "memory_kind": memory_kind,
            "content_schema_ref": content_schema_ref,
            "proposed_content": typed_content,
            "applicability_scope": applicability_scope,
            "evidence_refs": evidence_refs or [],
            "source_refs": source_refs or [],
            "source_dependency": source_dependency,
        }
        self._validate_proposal(proposal, "shadow.memory.correction-invalid")
        return MemoryCandidate(
            candidate_id=self._candidate_id("correct", submitted_by, owner_ref, space_id, proposal),
            submitted_by=submitted_by,
            owner_ref=owner_ref,
            space_id=space_id,
            payload=proposal,
        )

    def commit_correction(
        self, candidate: MemoryCandidate, *, idempotency_key: str
    ) -> dict[str, Any]:
        self._require_available()
        proposal = candidate.payload
        target = proposal["targets"][0]
        memory_id = target["memory_ref"]["record_id"]
        expected_version = target["expected_version"]
        current = self._load_target(
            memory_id,
            expected_version,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            allow_stale=True,
        )
        payload = self._corrected_payload(
            current, proposal, candidate.candidate_id, expected_version
        )
        operation = self._memory_operation(
            operation_id=f"operation-{memory_id}-correction-{expected_version}",
            operation="update",
            record_id=memory_id,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            created_by=candidate.submitted_by,
            typed_payload=payload,
            expected_version=expected_version,
        )
        result = self._commit(
            operations=[operation],
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(proposal),
            commit_request_id=f"commit-request-{candidate.candidate_id}",
            actor_ref=candidate.submitted_by,
        )
        return self._committed_record(result, memory_id)

    def propose_merge(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        targets: list[dict[str, Any]],
        memory_kind: str,
        content_schema_ref: str,
        typed_content: Any,
        applicability_scope: dict[str, Any],
        evidence_refs: list[dict[str, Any]] | None = None,
        source_refs: list[str] | None = None,
        source_dependency: str = "independent",
    ) -> MemoryCandidate:
        proposal = {
            "proposed_operation": "merge",
            "targets": targets,
            "memory_kind": memory_kind,
            "content_schema_ref": content_schema_ref,
            "proposed_content": typed_content,
            "applicability_scope": applicability_scope,
            "evidence_refs": evidence_refs or [],
            "source_refs": source_refs or [],
            "source_dependency": source_dependency,
        }
        self._validate_proposal(proposal, "shadow.memory.merge-invalid")
        for target in targets:
            self._load_target(
                target["memory_ref"]["record_id"],
                target["expected_version"],
                owner_ref=owner_ref,
                space_id=space_id,
                allow_stale=False,
            )
        return MemoryCandidate(
            candidate_id=self._candidate_id("merge", submitted_by, owner_ref, space_id, proposal),
            submitted_by=submitted_by,
            owner_ref=owner_ref,
            space_id=space_id,
            payload=proposal,
        )

    def commit_merge(self, candidate: MemoryCandidate, *, idempotency_key: str) -> dict[str, Any]:
        self._require_available()
        proposal = candidate.payload
        target_records = [
            self._load_target(
                target["memory_ref"]["record_id"],
                target["expected_version"],
                owner_ref=candidate.owner_ref,
                space_id=candidate.space_id,
                allow_stale=True,
            )
            for target in proposal["targets"]
        ]
        memory_id = f"memory-{sha256_digest({'candidate': candidate.candidate_id, 'key': idempotency_key})[7:31]}"
        merged_payload = {
            "memory_kind": proposal["memory_kind"],
            "content_schema_ref": proposal["content_schema_ref"],
            "typed_content": proposal["proposed_content"],
            "applicability_scope": proposal["applicability_scope"],
            "evidence_refs": proposal["evidence_refs"],
            "source_refs": proposal["source_refs"],
            "source_dependency": proposal["source_dependency"],
            "memory_state": "active",
            "supersedes_memory_refs": [
                {
                    "record_id": target["memory_ref"]["record_id"],
                    "version": target["expected_version"],
                }
                for target in proposal["targets"]
            ],
            "created_from_ref": {"record_id": candidate.candidate_id},
        }
        operations = [
            self._memory_operation(
                operation_id=f"operation-{memory_id}-create",
                operation="create",
                record_id=memory_id,
                owner_ref=candidate.owner_ref,
                space_id=candidate.space_id,
                created_by=candidate.submitted_by,
                typed_payload=merged_payload,
            )
        ]
        for target, record in zip(proposal["targets"], target_records, strict=True):
            superseded_payload = deepcopy(record["typed_payload"])
            superseded_payload["memory_state"] = "superseded"
            operations.append(
                self._memory_operation(
                    operation_id=(
                        f"operation-{target['memory_ref']['record_id']}-supersede-"
                        f"{target['expected_version']}"
                    ),
                    operation="transition",
                    record_id=target["memory_ref"]["record_id"],
                    owner_ref=candidate.owner_ref,
                    space_id=candidate.space_id,
                    created_by=candidate.submitted_by,
                    typed_payload=superseded_payload,
                    expected_version=target["expected_version"],
                )
            )
        result = self._commit(
            operations=operations,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(proposal),
            commit_request_id=f"commit-request-{candidate.candidate_id}",
            actor_ref=candidate.submitted_by,
        )
        return self._committed_record(result, memory_id)

    def logical_delete(
        self,
        *,
        memory_id: str,
        expected_version: int,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        current = self._load_target(
            memory_id,
            expected_version,
            owner_ref=owner_ref,
            space_id=space_id,
            allow_stale=True,
        )
        operation = self._memory_operation(
            operation_id=f"operation-{memory_id}-logical-delete-{expected_version}",
            operation="logical_delete",
            record_id=memory_id,
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=submitted_by,
            typed_payload=deepcopy(current["typed_payload"]),
            expected_version=expected_version,
            record_state="logically_deleted",
        )
        result = self._commit(
            operations=[operation],
            owner_ref=owner_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(
                {
                    "operation": "logical_delete",
                    "record_id": memory_id,
                    "expected_version": expected_version,
                }
            ),
            commit_request_id=f"commit-request-{memory_id}-logical-delete-{expected_version}",
            actor_ref=submitted_by,
        )
        return self._committed_record(result, memory_id)

    def list_memories(
        self, *, owner_ref: str | None = None, space_id: str | None = None
    ) -> list[dict[str, Any]]:
        records = self.repository.query_heads(
            owner_refs={owner_ref} if owner_ref else None,
            space_ids={space_id} if space_id else None,
            record_types={"shadow.profile.memory"},
            record_states={"active", "logically_deleted", "erased"},
            limit=None,
        )
        return [
            record
            for record in sorted(records, key=lambda item: item["record_id"])
            if record["record_state"] == "active"
            and record["typed_payload"].get("memory_state") == "active"
        ]

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        return self.repository.get(memory_id)

    def _candidate_id(
        self,
        operation: str,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        proposal: dict[str, Any],
    ) -> str:
        return f"memory-candidate-{sha256_digest({'operation': operation, 'submitted_by': submitted_by, 'owner': owner_ref, 'space': space_id, 'proposal': proposal})[7:31]}"

    def _validate_proposal(self, proposal: dict[str, Any], error_code: str) -> None:
        try:
            self.registry.validate(proposal, f"{PROFILE_SCHEMA}#/$defs/MemoryProposalPayload")
        except JsonSchemaValidationError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code=error_code,
                    category="validation",
                    message="Memory lifecycle proposal does not satisfy the Memory Profile contract.",
                    typed_details={"path": list(exc.absolute_path), "detail": exc.message},
                )
            ) from exc

    def _require_available(self) -> None:
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable; Memory was not committed.",
                    retryable=True,
                )
            )

    def _target_ref(self, memory_id: str, expected_version: int) -> dict[str, Any]:
        return {
            "memory_ref": StableRecordRef(record_id=memory_id).model_dump(mode="json"),
            "expected_version": expected_version,
        }

    def _load_target(
        self,
        memory_id: str,
        expected_version: int,
        *,
        owner_ref: str,
        space_id: str,
        allow_stale: bool,
    ) -> dict[str, Any]:
        self._require_available()
        head = self.repository.get(memory_id)
        target = self.repository.get(memory_id, expected_version)
        if head is None or target is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.not-found",
                    category="validation",
                    message=f"Memory {memory_id} was not found.",
                    typed_details={"record_id": memory_id, "expected_version": expected_version},
                )
            )
        if (
            head["owner_ref"] != owner_ref
            or head["space_id"] != space_id
            or target["owner_ref"] != owner_ref
            or target["space_id"] != space_id
        ):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.owner-space-mismatch",
                    category="unauthorized",
                    message="Memory owner or space does not match the write principal.",
                    typed_details={
                        "record_id": memory_id,
                        "owner_ref": owner_ref,
                        "space_id": space_id,
                    },
                )
            )
        target_is_active = (
            target["record_state"] == "active"
            and target["typed_payload"].get("memory_state") == "active"
        )
        stale_non_active = not target_is_active and head["version"] > expected_version
        if not target_is_active and not (allow_stale and stale_non_active):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.head-not-active",
                    category="conflict",
                    message=f"Memory {memory_id} is not an active Memory head.",
                    typed_details={"record_id": memory_id, "current_version": head["version"]},
                )
            )
        return target

    def _corrected_payload(
        self,
        current: dict[str, Any],
        proposal: dict[str, Any],
        candidate_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        return {
            "memory_kind": proposal["memory_kind"],
            "content_schema_ref": proposal["content_schema_ref"],
            "typed_content": proposal["proposed_content"],
            "applicability_scope": proposal["applicability_scope"],
            "evidence_refs": proposal["evidence_refs"],
            "source_refs": proposal["source_refs"],
            "source_dependency": proposal["source_dependency"],
            "memory_state": "active",
            "supersedes_memory_refs": current["typed_payload"].get("supersedes_memory_refs", []),
            "supersedes_version": expected_version,
            "created_from_ref": {"record_id": candidate_id},
        }

    def _memory_operation(
        self,
        *,
        operation_id: str,
        operation: str,
        record_id: str,
        owner_ref: str,
        space_id: str,
        created_by: str,
        typed_payload: dict[str, Any],
        expected_version: int | None = None,
        record_state: str = "active",
        origin_type: str = "shadow.origin.user-command",
        origin_ref: str | None = None,
    ) -> CommitOperation:
        return CommitOperation(
            operation_id=operation_id,
            operation=operation,
            record_id=record_id,
            record_type="shadow.profile.memory",
            target_schema_ref=f"{PROFILE_SCHEMA}#/$defs/MemoryPayload",
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=created_by,
            data_classification="personal",
            provenance=Provenance(
                origin_type=origin_type, origin_ref=origin_ref or operation_id
            ),
            retention_policy_ref=RETENTION_REF,
            record_state=record_state,
            typed_payload=typed_payload,
            expected_version=expected_version,
        )

    def _commit(
        self,
        *,
        operations: list[CommitOperation],
        owner_ref: str,
        space_id: str,
        idempotency_key: str,
        request_digest: str,
        commit_request_id: str,
        actor_ref: str,
    ) -> Any:
        result = self.authority.commit(
            CommitPlan(
                commit_request_id=commit_request_id,
                idempotency_scope=f"memory:{owner_ref}:{space_id}",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                actor_ref=actor_ref,
                operations=operations,
                prepared_at=utc_timestamp(),
            )
        )
        if result.outcome in {"conflict", "failed"}:
            if result.outcome == "conflict":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.repository.expected-version-conflict",
                        category="conflict",
                        message="Memory expected version does not match the current head.",
                        typed_details=result.model_dump(mode="json", exclude_none=True),
                    )
                )
            structured = result.structured_error or {}
            raise ShadowDomainError(
                ShadowError(
                    code=structured.get("code", "shadow.memory.commit-failed"),
                    category=structured.get("category", "validation"),
                    message=structured.get("message", "Memory lifecycle commit failed."),
                    typed_details=structured or result.model_dump(mode="json", exclude_none=True),
                )
            )
        return result

    def _committed_record(self, result: Any, record_id: str) -> dict[str, Any]:
        operation_result = next(
            item for item in result.operation_results if item.record_id == record_id
        )
        record = self.repository.get(record_id, operation_result.resulting_version)
        if record is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.record-missing",
                    category="internal",
                    message=f"Committed Memory {record_id} could not be read back.",
                )
            )
        return record
