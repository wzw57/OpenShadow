from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .adapters import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityRequirement,
    ExecutionBinding,
)
from .errors import ShadowDomainError, ShadowError
from .ids import sha256_digest
from .models import ExecutionRequest
from .runtime import RuntimeAdapter, request_text


@dataclass(frozen=True, slots=True)
class DispatchResult:
    request: ExecutionRequest
    binding: ExecutionBinding
    output: Any
    adapter_id: str
    replayed: bool = False


class ExecutionDispatcher:
    """Select and invoke a registered Runtime through one typed boundary."""

    def __init__(self, adapters: AdapterRegistry | None = None) -> None:
        self.adapters = adapters or AdapterRegistry()
        self._runtimes: dict[str, RuntimeAdapter] = {}
        self._receipts: dict[tuple[str, str], tuple[str, DispatchResult]] = {}

    def register_adapter(self, adapter: RuntimeAdapter) -> AdapterDescriptor:
        body = adapter.describe()
        descriptor = AdapterDescriptor(**body, descriptor_digest=sha256_digest(body))
        self.adapters.register(descriptor)
        self._runtimes[descriptor.descriptor_id] = adapter
        return descriptor

    def dispatch(
        self,
        request: ExecutionRequest,
        *,
        target_kind: str,
        required_capabilities: list[str | CapabilityRequirement] | None = None,
        idempotency_scope: str = "execution",
        approval_state: str = "approved",
        revoked: bool = False,
        now: datetime | None = None,
    ) -> DispatchResult:
        self._check_authorization(approval_state=approval_state, revoked=revoked)
        self._check_deadline(request.deadline, now=now)
        requirements = self._requirements(required_capabilities or [])
        adapter_id, descriptor = self._select(target_kind)
        binding = self.adapters.bind(
            descriptor_id=adapter_id,
            target_kind=target_kind,
            required_capabilities=requirements,
            binding_id=request.binding_ref.record_id,
            scope_ref={"record_id": request.run_ref.record_id},
            capability_envelope_ref=request.capability_envelope_snapshot.envelope_ref.model_dump(
                mode="json"
            ),
            selection_source_ref={"source": "shadow.execution-dispatcher"},
        )
        digest = sha256_digest(
            {
                "request": request.model_dump(mode="json"),
                "target_kind": target_kind,
                "required_capabilities": [requirement.model_dump(mode="json") for requirement in requirements],
            }
        )
        receipt_key = (idempotency_scope, request.idempotency_key)
        prior = self._receipts.get(receipt_key)
        if prior is not None:
            if prior[0] != digest:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.execution.idempotency-mismatch",
                        category="conflict",
                        message="Execution idempotency key was reused with different input.",
                        typed_details={"idempotency_scope": idempotency_scope},
                    )
                )
            return DispatchResult(
                request=prior[1].request,
                binding=prior[1].binding,
                output=prior[1].output,
                adapter_id=prior[1].adapter_id,
                replayed=True,
            )
        output = self._invoke(self._runtimes[adapter_id], request)
        result = DispatchResult(
            request=request,
            binding=binding,
            output=output,
            adapter_id=adapter_id,
        )
        self._receipts[receipt_key] = (digest, result)
        return result

    @staticmethod
    def _invoke(adapter: RuntimeAdapter, request: ExecutionRequest) -> Any:
        """Call typed adapters while keeping a bounded v0.1 text shim.

        The shim is deliberately local to the Dispatcher.  New adapters must
        implement the typed port; legacy test/deployment adapters whose first
        parameter is named ``text`` continue to work during R3 migration.
        """
        parameters = list(inspect.signature(adapter.execute).parameters.values())
        if parameters and parameters[0].name == "text":
            return adapter.execute(request_text(request))  # type: ignore[arg-type]
        return adapter.execute(request)

    @staticmethod
    def _requirements(
        required_capabilities: list[str | CapabilityRequirement],
    ) -> list[CapabilityRequirement]:
        result: list[CapabilityRequirement] = []
        for requirement in required_capabilities:
            if isinstance(requirement, CapabilityRequirement):
                result.append(requirement)
            else:
                result.append(
                    CapabilityRequirement(
                        capability_id=requirement,
                        version_range=">=1.0.0",
                    )
                )
        return result

    def _select(self, target_kind: str) -> tuple[str, AdapterDescriptor]:
        for adapter_id in self._runtimes:
            descriptor = self.adapters.descriptor(adapter_id)
            if target_kind in descriptor.supported_target_kinds:
                return adapter_id, descriptor
        raise ShadowDomainError(
            ShadowError(
                code="shadow.execution.target-unsupported",
                category="incompatible",
                message=f"No registered Runtime supports target kind {target_kind}.",
            )
        )

    @staticmethod
    def _check_authorization(*, approval_state: str, revoked: bool) -> None:
        if revoked:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.capability-revoked",
                    category="unauthorized",
                    message="Execution capability has been revoked.",
                )
            )
        if approval_state != "approved":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.approval-required",
                    category="unauthorized",
                    message="Execution requires an approved capability envelope.",
                )
            )

    @staticmethod
    def _check_deadline(deadline: str | None, *, now: datetime | None) -> None:
        if deadline is None:
            return
        try:
            expires_at = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.invalid-deadline",
                    category="validation",
                    message="Execution deadline is not a valid timestamp.",
                )
            ) from exc
        current = now or datetime.now(UTC)
        if expires_at <= current:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.deadline-expired",
                    category="timeout",
                    message="Execution deadline has expired.",
                    retryable=False,
                )
            )


__all__ = ["DispatchResult", "ExecutionDispatcher"]
