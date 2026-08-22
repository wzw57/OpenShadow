from __future__ import annotations

from typing import Any, Protocol

from pydantic import Field, model_validator
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    Provenance,
    RecordVersionRef,
    StableRecordRef,
    StrictModel,
)
from shadow_kernel.repository import CanonicalRepository

TOMBSTONE_SCHEMA = "https://schemas.openshadow.dev/contracts/kernel/1.0.0#/$defs/TombstonePayload"


class PhysicalEraseRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    record_id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)
    erasure_ref: StableRecordRef
    relation_refs: list[StableRecordRef] = Field(default_factory=list, max_length=100)
    request_id: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_relations(self) -> PhysicalEraseRequest:
        refs = [ref.record_id for ref in self.relation_refs]
        if len(refs) != len(set(refs)):
            raise ValueError("relation_refs must be unique")
        return self


class PhysicalEraseResult(StrictModel):
    result_state: str
    record_ref: RecordVersionRef
    erasure_ref: StableRecordRef
    purged_version_count: int = Field(ge=0)
    commit_id: str | None = None
    replayed: bool = False
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)


class ErasureAdapter(Protocol):
    def quiesce(self, request: PhysicalEraseRequest, record: dict[str, Any]) -> None: ...

    def erase(self, request: PhysicalEraseRequest, record: dict[str, Any]) -> None: ...

    def finalize(self, request: PhysicalEraseRequest, tombstone: dict[str, Any]) -> None: ...


def physical_erase_result_digest(result: PhysicalEraseResult) -> str:
    return sha256_digest(
        {
            "record_ref": result.record_ref.model_dump(mode="json"),
            "erasure_ref": result.erasure_ref.model_dump(mode="json"),
            "commit_id": result.commit_id,
        }
    )


class PhysicalEraseService:
    """Execute one irreversible erase through an explicit Adapter boundary."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        adapter: ErasureAdapter,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.adapter = adapter

    def erase(self, request: PhysicalEraseRequest) -> PhysicalEraseResult:
        request = PhysicalEraseRequest.model_validate(request)
        if not self.repository.available:
            raise RepositoryUnavailable()
        scope = f"erasure:{request.principal_ref}:{request.space_id}"
        request_digest = sha256_digest(request.model_dump(mode="json"))
        prior = self.repository.idempotency_result(scope, request.idempotency_key)
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise self._error(
                    "shadow.erasure.replay-conflict",
                    "Erasure idempotency key was reused with different content.",
                    category="conflict",
                )
            if prior["result"].outcome == "committed":
                return self._complete_replay(request, prior["result"])
            raise self._error(
                "shadow.erasure.version-conflict",
                "The prior erasure attempt was not committed.",
                category="conflict",
                details=prior["result"].model_dump(mode="json", exclude_none=True),
            )

        record = self.repository.get(request.record_id)
        if record is None:
            raise self._error(
                "shadow.erasure.not-found", "The record to erase was not found."
            )
        self._check_owner(record, request)
        if record["record_state"] == "erased":
            raise self._error(
                "shadow.erasure.already-erased",
                "The record is already erased and cannot be erased again.",
                category="conflict",
            )
        if record["version"] != request.expected_version:
            raise self._error(
                "shadow.erasure.version-conflict",
                "Erasure expected version does not match the current head.",
                category="conflict",
                details={"current_version": record["version"]},
            )

        self._adapter_call("quiesce", request, record)
        self._adapter_call("erase", request, record)
        tombstone = {
            "erased": True,
            "erasure_ref": request.erasure_ref.model_dump(mode="json"),
            "non_sensitive_relation_refs": [
                ref.model_dump(mode="json") for ref in request.relation_refs
            ],
        }
        try:
            commit = self.authority.commit(
                CommitPlan(
                    commit_request_id=f"commit-request-{request.request_id}",
                    idempotency_scope=scope,
                    idempotency_key=request.idempotency_key,
                    request_digest=request_digest,
                    actor_ref=request.principal_ref,
                    operations=[
                        CommitOperation(
                            operation_id=f"operation-erase-{request.record_id}-{request.expected_version}",
                            operation="erase",
                            record_id=request.record_id,
                            record_type=record["record_type"],
                            target_schema_ref=TOMBSTONE_SCHEMA,
                            owner_ref=request.principal_ref,
                            space_id=request.space_id,
                            created_by=request.principal_ref,
                            data_classification=record["data_classification"],
                            provenance=Provenance(
                                origin_type="shadow.origin.erasure",
                                origin_ref=request.erasure_ref.record_id,
                            ),
                            retention_policy_ref=StableRecordRef(record_id="retention-default"),
                            record_state="erased",
                            typed_payload=tombstone,
                            expected_version=request.expected_version,
                        )
                    ],
                    prepared_at=utc_timestamp(),
                )
            )
        except RepositoryUnavailable:
            raise
        if commit.outcome == "conflict":
            raise self._error(
                "shadow.erasure.version-conflict",
                "Erasure CAS conflict; the Canonical record was not marked erased.",
                category="conflict",
                details=commit.model_dump(mode="json", exclude_none=True),
            )
        if commit.outcome == "failed":
            structured = commit.structured_error or {}
            if structured.get("code") == "shadow.repository.idempotency-mismatch":
                raise self._error(
                    "shadow.erasure.replay-conflict",
                    "Erasure idempotency key was reused with different content.",
                    category="conflict",
                    details=structured,
                )
            raise self._error(
                "shadow.erasure.commit-failed",
                "Erasure Tombstone commit failed.",
                details=structured,
            )

        operation_result = commit.operation_results[0]
        if operation_result.resulting_version is None:
            raise self._error(
                "shadow.erasure.commit-missing-result",
                "Erasure commit did not return a Tombstone version.",
                category="internal",
            )
        return self._finalize(
            request,
            record_id=request.record_id,
            resulting_version=operation_result.resulting_version,
            commit_id=commit.commit_id,
            tombstone=tombstone,
            replayed=False,
        )

    def _complete_replay(self, request: PhysicalEraseRequest, prior: Any) -> PhysicalEraseResult:
        operation_result = prior.operation_results[0]
        if operation_result.resulting_version is None:
            raise self._error(
                "shadow.erasure.commit-missing-result",
                "Prior erasure commit did not contain a Tombstone version.",
                category="internal",
            )
        tombstone = self.repository.get(request.record_id, operation_result.resulting_version)
        if tombstone is None or tombstone["record_state"] != "erased":
            raise self._error(
                "shadow.erasure.finalize-failed",
                "Erasure Tombstone is not readable after a committed replay.",
                category="unavailable",
                details={"record_id": request.record_id},
            )
        return self._finalize(
            request,
            record_id=request.record_id,
            resulting_version=operation_result.resulting_version,
            commit_id=prior.commit_id,
            tombstone=tombstone["typed_payload"],
            replayed=True,
        )

    def _finalize(
        self,
        request: PhysicalEraseRequest,
        *,
        record_id: str,
        resulting_version: int,
        commit_id: str | None,
        tombstone: dict[str, Any],
        replayed: bool,
    ) -> PhysicalEraseResult:
        try:
            purged = self.repository.erase_history(record_id, resulting_version)
            self.adapter.finalize(request, tombstone)
        except (RepositoryUnavailable, ShadowDomainError) as exc:
            raise self._error(
                "shadow.erasure.finalize-failed",
                "Erasure committed a Tombstone but final cleanup is incomplete.",
                category="unavailable",
                details={
                    "record_id": record_id,
                    "tombstone_version": resulting_version,
                    "cause": str(exc),
                },
            ) from exc
        result = PhysicalEraseResult(
            result_state="replayed" if replayed else "committed",
            record_ref=RecordVersionRef(record_id=record_id, version=resulting_version),
            erasure_ref=request.erasure_ref,
            purged_version_count=purged,
            commit_id=commit_id,
            replayed=replayed,
        )
        return result.model_copy(update={"result_digest": physical_erase_result_digest(result)})

    def _adapter_call(
        self, method_name: str, request: PhysicalEraseRequest, record: dict[str, Any]
    ) -> None:
        try:
            getattr(self.adapter, method_name)(request, record)
        except (RepositoryUnavailable, ShadowDomainError) as exc:
            raise self._error(
                "shadow.erasure.adapter-unavailable",
                f"Erasure Adapter {method_name} step is unavailable.",
                category="unavailable",
            ) from exc

    @staticmethod
    def _check_owner(record: dict[str, Any], request: PhysicalEraseRequest) -> None:
        if record["owner_ref"] != request.principal_ref or record["space_id"] != request.space_id:
            raise PhysicalEraseService._error(
                "shadow.erasure.owner-space-mismatch",
                "Erasure owner or space does not match the record.",
                category="unauthorized",
            )

    @staticmethod
    def _error(
        code: str,
        message: str,
        *,
        category: str = "validation",
        details: Any | None = None,
    ) -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(code=code, category=category, message=message, typed_details=details)
        )


__all__ = [
    "ErasureAdapter",
    "PhysicalEraseRequest",
    "PhysicalEraseResult",
    "PhysicalEraseService",
    "physical_erase_result_digest",
]
