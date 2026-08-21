from __future__ import annotations

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
            self.registry.validate(operation.typed_payload, operation.target_schema_ref)
        result = self.repository.commit_batch(plan)
        if result.outcome in {"committed", "idempotent_replay"}:
            for operation_result in result.operation_results:
                envelope = self.repository.get(
                    operation_result.record_id, operation_result.resulting_version
                )
                if envelope:
                    self.registry.validate_envelope(envelope)
        return result
