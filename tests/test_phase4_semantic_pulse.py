from __future__ import annotations

from pathlib import Path

import pytest
from shadow_adapters import DeterministicSemanticPulseAdapter
from shadow_application import SemanticPulseService
from shadow_kernel.admission import AdmissionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _inputs() -> tuple[dict[str, object], dict[str, object]]:
    trigger = {
        "trigger_id": "trigger-calendar-1",
        "trigger_kind": "shadow.pulse.calendar-change",
        "source_ref": "integration:calendar",
        "event_ref": "calendar-event-1",
        "observed_at": "2026-08-22T08:00:00Z",
        "principal_ref": "principal-pulse",
        "space_id": "space-pulse",
    }
    observation = {
        "source_ref": "integration:calendar",
        "source_status": "available",
        "observed_at": "2026-08-22T08:00:00Z",
        "evidence_refs": ["calendar-event-1"],
        "summary": "calendar changed",
    }
    return trigger, observation


def _service() -> tuple[SemanticPulseService, DeterministicSemanticPulseAdapter]:
    adapter = DeterministicSemanticPulseAdapter()
    return SemanticPulseService(ContractRegistry(ROOT), adapter), adapter


def _produce(service: SemanticPulseService) -> dict[str, object]:
    trigger, observation = _inputs()
    return service.produce_proposal(
        trigger=trigger,
        observation=observation,
        proposal_kind="shadow.task-proposal",
        input_schema_ref="https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TaskProposalPayload",
        typed_payload={"proposed_operation": "create", "task_key": "calendar-follow-up"},
        budget={"max_cost": 1},
        cooldown_key="calendar-follow-up",
        expires_at="2099-01-01T00:00:00Z",
        idempotency_key="pulse-key-1",
    ).proposal


def test_pulse_produces_stable_proposal_and_reenters_admission(tmp_path: Path) -> None:
    service, adapter = _service()
    proposal = _produce(service)
    replay = _produce(service)
    assert proposal["proposal_id"] == replay["proposal_id"]
    assert proposal["proposal_kind"] == "shadow.task-proposal"
    assert adapter.calls == 2

    repository = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'pulse.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    admission = AdmissionService(repository, CommitAuthority(repository, registry))
    admitted = service.admit_proposal(proposal=proposal, endpoint_ref="endpoint-pulse", admission=admission)
    assert admitted.decision == "accepted"
    assert admitted.run is not None
    records = repository.query(record_types={"shadow.profile.task", "shadow.profile.memory", "shadow.profile.state", "shadow.profile.action"}, limit=100)
    assert records == []


def test_source_unavailable_budget_and_expiry_do_not_produce_work() -> None:
    service, _ = _service()
    trigger, observation = _inputs()
    observation["source_status"] = "unavailable"
    with pytest.raises(ShadowDomainError) as source_error:
        service.produce_proposal(
            trigger=trigger, observation=observation, proposal_kind="shadow.task-proposal",
            input_schema_ref="https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TaskProposalPayload",
            typed_payload={}, budget={"max_cost": 1}, cooldown_key="calendar-follow-up",
            expires_at="2099-01-01T00:00:00Z", idempotency_key="pulse-source",
        )
    assert source_error.value.error.code == "shadow.pulse.source-unavailable"

    trigger, observation = _inputs()
    with pytest.raises(ShadowDomainError) as budget_error:
        service.produce_proposal(
            trigger=trigger, observation=observation, proposal_kind="shadow.task-proposal",
            input_schema_ref="https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TaskProposalPayload",
            typed_payload={}, budget={"max_cost": 0}, cooldown_key="calendar-follow-up",
            expires_at="2099-01-01T00:00:00Z", idempotency_key="pulse-budget",
        )
    assert budget_error.value.error.code == "shadow.pulse.budget-exhausted"

    with pytest.raises(ShadowDomainError) as expiry_error:
        service.produce_proposal(
            trigger=trigger, observation=observation, proposal_kind="shadow.task-proposal",
            input_schema_ref="https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TaskProposalPayload",
            typed_payload={}, budget={"max_cost": 1}, cooldown_key="calendar-follow-up",
            expires_at="2020-01-01T00:00:00Z", idempotency_key="pulse-expiry",
        )
    assert expiry_error.value.error.code == "shadow.pulse.expired"


def test_adapter_cannot_change_owner_or_stable_id() -> None:
    class MutatingAdapter(DeterministicSemanticPulseAdapter):
        def propose(self, request: dict[str, object]) -> dict[str, object]:
            proposal = super().propose(request)
            proposal["principal_ref"] = "other"
            return proposal

    service = SemanticPulseService(ContractRegistry(ROOT), MutatingAdapter())
    trigger, observation = _inputs()
    with pytest.raises(ShadowDomainError) as error:
        service.produce_proposal(
            trigger=trigger, observation=observation, proposal_kind="shadow.task-proposal",
            input_schema_ref="https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TaskProposalPayload",
            typed_payload={"proposed_operation": "create"}, budget={"max_cost": 1},
            cooldown_key="calendar-follow-up", expires_at="2099-01-01T00:00:00Z", idempotency_key="pulse-owner",
        )
    assert error.value.error.code == "shadow.pulse.unauthorized"
