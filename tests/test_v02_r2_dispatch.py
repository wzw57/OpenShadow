from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from shadow_adapters import DeterministicTestAdapter
from shadow_kernel.dispatch import ExecutionDispatcher
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.models import (
    CapabilityEnvelopeSnapshot,
    ExecutionRequest,
    RecordVersionRef,
    StableRecordRef,
)
from shadow_kernel.registry import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]


def _request(*, key: str = "dispatch-1", deadline: str | None = None) -> ExecutionRequest:
    return ExecutionRequest(
        execution_request_id="execution-request-1",
        run_ref=RecordVersionRef(record_id="run-1", version=1),
        attempt_ref=RecordVersionRef(record_id="attempt-1", version=1),
        binding_ref=RecordVersionRef(record_id="binding-1", version=1),
        idempotency_key=key,
        capability_envelope_snapshot=CapabilityEnvelopeSnapshot(
            envelope_ref=StableRecordRef(record_id="envelope-1"),
            version=1,
            digest="sha256:" + "0" * 64,
            effective_constraints={"allowed_side_effects": []},
        ),
        input_schema_ref="https://schemas.openshadow.dev/contracts/execution/1.0.0#/$defs/ExecutionRequest",
        typed_input={"text": "hello"},
        correlation_id="correlation-1",
        submitted_at="2026-08-23T00:00:00Z",
        deadline=deadline,
    )


def test_execution_request_matches_offline_contract() -> None:
    registry = ContractRegistry(ROOT)
    registry.validate(
        _request().model_dump(mode="json", exclude_none=True),
        "https://schemas.openshadow.dev/contracts/execution/1.0.0#/$defs/ExecutionRequest",
    )


def test_dispatcher_uses_typed_request_and_replays_without_provider_call() -> None:
    class CountingAdapter(DeterministicTestAdapter):
        calls = 0

        def execute(self, request):  # type: ignore[no-untyped-def]
            self.calls += 1
            return super().execute(request)

    adapter = CountingAdapter()
    dispatcher = ExecutionDispatcher()
    descriptor = dispatcher.register_adapter(adapter)
    first = dispatcher.dispatch(
        _request(),
        target_kind=adapter.target_kind,
        idempotency_scope="run:run-1",
    )
    replay = dispatcher.dispatch(
        _request(),
        target_kind=adapter.target_kind,
        idempotency_scope="run:run-1",
    )
    assert descriptor.descriptor_id == "shadow.adapter.deterministic"
    assert first.output.text == "Echo: hello"
    assert first.replayed is False
    assert replay.replayed is True
    assert adapter.calls == 1


def test_dispatcher_rejects_capability_target_approval_revocation_and_expiry() -> None:
    dispatcher = ExecutionDispatcher()
    adapter = DeterministicTestAdapter()
    dispatcher.register_adapter(adapter)

    with pytest.raises(ShadowDomainError) as capability:
        dispatcher.dispatch(
            _request(key="capability"),
            target_kind=adapter.target_kind,
            required_capabilities=["shadow.capability.missing"],
        )
    assert capability.value.error.code == "shadow.adapter.required-capability-unknown"

    with pytest.raises(ShadowDomainError) as target:
        dispatcher.dispatch(_request(key="target"), target_kind="example.unknown")
    assert target.value.error.code == "shadow.execution.target-unsupported"

    with pytest.raises(ShadowDomainError) as approval:
        dispatcher.dispatch(
            _request(key="approval"), target_kind=adapter.target_kind, approval_state="pending"
        )
    assert approval.value.error.code == "shadow.execution.approval-required"

    with pytest.raises(ShadowDomainError) as revoked:
        dispatcher.dispatch(
            _request(key="revoked"), target_kind=adapter.target_kind, revoked=True
        )
    assert revoked.value.error.code == "shadow.execution.capability-revoked"

    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(ShadowDomainError) as deadline:
        dispatcher.dispatch(
            _request(key="expired", deadline=expired), target_kind=adapter.target_kind
        )
    assert deadline.value.error.code == "shadow.execution.deadline-expired"


def test_dispatcher_rejects_idempotency_mismatch() -> None:
    dispatcher = ExecutionDispatcher()
    adapter = DeterministicTestAdapter()
    dispatcher.register_adapter(adapter)
    dispatcher.dispatch(_request(key="same"), target_kind=adapter.target_kind)
    different = _request(key="same").model_copy(update={"typed_input": {"text": "different"}})
    with pytest.raises(ShadowDomainError) as mismatch:
        dispatcher.dispatch(different, target_kind=adapter.target_kind)
    assert mismatch.value.error.code == "shadow.execution.idempotency-mismatch"
