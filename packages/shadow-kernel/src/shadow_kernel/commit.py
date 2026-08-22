from __future__ import annotations

from jsonschema import ValidationError

from .errors import ShadowDomainError, ShadowError
from .models import CommitBatchResult, CommitPlan
from .registry import ContractRegistry
from .repository import CanonicalRepository


class CommitAuthority:
    """The only Phase 0 entry point that can create Canonical versions."""

    def __init__(self, repository: CanonicalRepository, registry: ContractRegistry):
        self.repository = repository
        self.registry = registry

    def commit(self, plan: CommitPlan) -> CommitBatchResult:
        for operation in plan.operations:
            try:
                self.registry.validate(operation.typed_payload, operation.target_schema_ref)
            except ValidationError as exc:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.validation-failed",
                        category="validation",
                        message="Commit payload does not satisfy its declared contract.",
                        typed_details={
                            "schema_ref": operation.target_schema_ref,
                            "path": list(exc.absolute_path),
                            "detail": exc.message,
                        },
                    )
                ) from exc
        result = self.repository.commit_batch(plan)
        if result.outcome in {"committed", "idempotent_replay"}:
            for operation_result in result.operation_results:
                envelope = self.repository.get(
                    operation_result.record_id, operation_result.resulting_version
                )
                if envelope:
                    try:
                        self.registry.validate_envelope(envelope)
                    except ValidationError as exc:
                        raise ShadowDomainError(
                            ShadowError(
                                code="shadow.repository.invalid-envelope",
                                category="internal",
                                message="Repository returned an invalid Canonical Envelope.",
                                typed_details={
                                    "record_id": operation_result.record_id,
                                    "path": list(exc.absolute_path),
                                    "detail": exc.message,
                                },
                            )
                        ) from exc
        return result
