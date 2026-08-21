from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
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
    """Phase 1's narrow Candidate -> Commit boundary for user-authored Memory."""

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

    def commit_candidate(self, candidate: MemoryCandidate, *, idempotency_key: str) -> dict[str, Any]:
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

    def list_memories(
        self, *, owner_ref: str | None = None, space_id: str | None = None
    ) -> list[dict[str, Any]]:
        return self.repository.query(
            owner_refs={owner_ref} if owner_ref else None,
            space_ids={space_id} if space_id else None,
            record_types={"shadow.profile.memory"},
            record_states={"active"},
        )

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        return self.repository.get(memory_id)
