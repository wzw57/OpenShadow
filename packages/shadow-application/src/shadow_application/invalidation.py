from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import Field, model_validator
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import RecordVersionRef, StrictModel

from .memory import MemoryService


class MemorySourceInvalidationRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    source_ref: str = Field(min_length=1, max_length=1000)
    source_event_ref: str = Field(min_length=1, max_length=1000)
    source_state: Literal["unavailable", "deleted", "restored"]
    targets: list[RecordVersionRef] = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=255)
    request_id: str = Field(min_length=1, max_length=255)
    observed_at: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=4000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def require_unique_targets(self) -> MemorySourceInvalidationRequest:
        refs = [(target.record_id, target.version) for target in self.targets]
        if len(refs) != len(set(refs)):
            raise ValueError("targets must be unique")
        return self


class MemorySourceInvalidationTargetResult(StrictModel):
    record_ref: RecordVersionRef
    action: Literal["invalidated", "retained", "review_required", "unsupported"]
    previous_version: int | None = None
    resulting_version: int | None = None
    reason_code: str = Field(min_length=1, max_length=255)


class MemorySourceInvalidationResult(StrictModel):
    result_state: Literal[
        "committed", "no_change", "review_required", "unsupported", "unavailable"
    ]
    source_event_ref: str = Field(min_length=1, max_length=1000)
    targets: list[MemorySourceInvalidationTargetResult] = Field(
        default_factory=list, max_length=100
    )
    commit_id: str | None = None
    replayed: bool = False
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)
    failure_detail: dict[str, Any] | None = None


def memory_source_invalidation_digest(result: MemorySourceInvalidationResult) -> str:
    return sha256_digest(
        {
            "result_state": result.result_state,
            "source_event_ref": result.source_event_ref,
            "targets": [target.model_dump(mode="json") for target in result.targets],
            "commit_id": result.commit_id,
            "failure_detail": result.failure_detail,
        }
    )


class MemorySourceInvalidationService:
    """Apply validated source events through the existing Memory Commit boundary."""

    def __init__(self, memory_service: MemoryService) -> None:
        self.memory_service = memory_service

    def invalidate(
        self, request: MemorySourceInvalidationRequest
    ) -> MemorySourceInvalidationResult:
        request = MemorySourceInvalidationRequest.model_validate(request)
        if request.source_state == "restored":
            result = MemorySourceInvalidationResult(
                result_state="unsupported",
                source_event_ref=request.source_event_ref,
                targets=[
                    MemorySourceInvalidationTargetResult(
                        record_ref=target,
                        action="unsupported",
                        reason_code="source-restored-no-auto-reactivation",
                    )
                    for target in request.targets
                ],
                failure_detail={
                    "code": "shadow.memory.source-invalidation-invalid",
                    "detail": "Source restoration cannot reactivate invalidated Memory.",
                },
            )
            return result.model_copy(update={"result_digest": memory_source_invalidation_digest(result)})

        self._require_available()
        prepared: list[tuple[dict[str, Any], bool]] = []
        operations = []
        outcomes: list[MemorySourceInvalidationTargetResult] = []
        for target in request.targets:
            record = self._load_target(request, target)
            dependency = record["typed_payload"].get("source_dependency")
            if dependency not in {"independent", "dependent", "review_required"}:
                raise self._invalid("Memory source_dependency is not a valid Profile value.")
            if request.source_ref not in record["typed_payload"].get("source_refs", []):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.source-not-attached",
                        category="validation",
                        message="Source event does not match the target Memory source refs.",
                        typed_details={
                            "record_id": target.record_id,
                            "source_ref": request.source_ref,
                        },
                    )
                )
            if dependency == "independent":
                prepared.append((record, False))
                outcomes.append(
                    MemorySourceInvalidationTargetResult(
                        record_ref=target,
                        action="retained",
                        previous_version=record["version"],
                        reason_code="source-independent",
                    )
                )
                continue
            if dependency == "review_required":
                prepared.append((record, False))
                outcomes.append(
                    MemorySourceInvalidationTargetResult(
                        record_ref=target,
                        action="review_required",
                        previous_version=record["version"],
                        reason_code="source-review-required",
                    )
                )
                continue
            prepared.append((record, True))
            operations.append(
                self._invalidation_operation(request, record, target.version)
            )
            outcomes.append(
                MemorySourceInvalidationTargetResult(
                    record_ref=target,
                    action="invalidated",
                    previous_version=record["version"],
                    reason_code="source-dependent",
                )
            )

        if not operations:
            result_state: Literal["no_change", "review_required"] = (
                "review_required"
                if any(target.action == "review_required" for target in outcomes)
                else "no_change"
            )
            result = MemorySourceInvalidationResult(
                result_state=result_state,
                source_event_ref=request.source_event_ref,
                targets=outcomes,
            )
            return result.model_copy(update={"result_digest": memory_source_invalidation_digest(result)})

        try:
            commit_result = self.memory_service._commit(
                operations=operations,
                owner_ref=request.principal_ref,
                space_id=request.space_id,
                idempotency_key=request.idempotency_key,
                request_digest=sha256_digest(request.model_dump(mode="json")),
                commit_request_id=(
                    f"commit-request-source-invalidation-"
                    f"{sha256_digest({'event': request.source_event_ref, 'targets': [target.model_dump(mode='json') for target in request.targets]})[7:31]}"
                ),
                actor_ref=request.principal_ref,
            )
        except ShadowDomainError as exc:
            self._translate_commit_error(exc)
            raise

        operation_results = {
            item.record_id: item
            for item in commit_result.operation_results
        }
        resolved_targets = []
        for target in outcomes:
            operation_result = operation_results.get(target.record_ref.record_id)
            if target.action == "invalidated" and operation_result is not None:
                resolved_targets.append(
                    target.model_copy(
                        update={
                            "resulting_version": operation_result.resulting_version,
                        }
                    )
                )
            else:
                resolved_targets.append(target)
        result = MemorySourceInvalidationResult(
            result_state="committed",
            source_event_ref=request.source_event_ref,
            targets=resolved_targets,
            commit_id=commit_result.commit_id,
            replayed=commit_result.outcome == "idempotent_replay",
        )
        return result.model_copy(update={"result_digest": memory_source_invalidation_digest(result)})

    def _load_target(
        self, request: MemorySourceInvalidationRequest, target: RecordVersionRef
    ) -> dict[str, Any]:
        try:
            return self.memory_service._load_target(
                target.record_id,
                target.version,
                owner_ref=request.principal_ref,
                space_id=request.space_id,
                allow_stale=True,
            )
        except ShadowDomainError as exc:
            if exc.error.code == "shadow.memory.owner-space-mismatch":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.source-owner-space-mismatch",
                        category="unauthorized",
                        message="Source invalidation owner or space does not match the target.",
                        typed_details=exc.error.typed_details,
                    )
                ) from exc
            if exc.error.code == "shadow.memory.not-found":
                raise self._invalid("Source invalidation target was not found.") from exc
            if exc.error.code == "shadow.repository.unavailable":
                raise self._unavailable() from exc
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.source-head-conflict",
                    category="conflict",
                    message="Source invalidation target is not a compatible Memory head.",
                    typed_details=exc.error.typed_details,
                )
            ) from exc

    def _invalidation_operation(
        self,
        request: MemorySourceInvalidationRequest,
        record: dict[str, Any],
        expected_version: int,
    ) -> Any:
        payload = deepcopy(record["typed_payload"])
        payload["memory_state"] = "invalidated"
        payload["supersedes_version"] = expected_version
        payload["created_from_ref"] = {
            "record_id": f"source-event-{sha256_digest(request.source_event_ref)[7:31]}"
        }
        return self.memory_service._memory_operation(
            operation_id=(
                f"operation-{record['record_id']}-source-invalidation-{expected_version}"
            ),
            operation="transition",
            record_id=record["record_id"],
            owner_ref=request.principal_ref,
            space_id=request.space_id,
            created_by=request.principal_ref,
            typed_payload=payload,
            expected_version=expected_version,
            record_state="active",
            origin_type="shadow.origin.source-event",
            origin_ref=request.source_event_ref,
        )

    def _require_available(self) -> None:
        if not self.memory_service.repository.available:
            raise self._unavailable()

    @staticmethod
    def _invalid(message: str) -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(
                code="shadow.memory.source-invalidation-invalid",
                category="validation",
                message=message,
            )
        )

    @staticmethod
    def _unavailable() -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(
                code="shadow.memory.source-invalidation-unavailable",
                category="unavailable",
                message="Canonical Store is unavailable for source invalidation.",
                retryable=True,
            )
        )

    @staticmethod
    def _translate_commit_error(exc: ShadowDomainError) -> None:
        if exc.error.code == "shadow.repository.idempotency-mismatch":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.source-replay-conflict",
                    category="conflict",
                    message="Source event idempotency key was reused with different content.",
                    typed_details=exc.error.typed_details,
                )
            ) from exc
        if exc.error.code == "shadow.repository.expected-version-conflict":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.source-head-conflict",
                    category="conflict",
                    message="Source invalidation expected version does not match the current head.",
                    typed_details=exc.error.typed_details,
                )
            ) from exc
        if exc.error.category == "unavailable":
            raise MemorySourceInvalidationService._unavailable() from exc


__all__ = [
    "MemorySourceInvalidationRequest",
    "MemorySourceInvalidationResult",
    "MemorySourceInvalidationTargetResult",
    "MemorySourceInvalidationService",
    "memory_source_invalidation_digest",
]
