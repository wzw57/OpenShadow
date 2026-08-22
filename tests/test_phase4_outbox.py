from __future__ import annotations

from pathlib import Path

import pytest
from shadow_adapters import DeterministicOutboxAdapter
from shadow_application import ActionService, OutboxService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path: Path) -> tuple[SqliteCanonicalRepository, ActionService, OutboxService]:
    repository = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'outbox.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, ActionService(repository, authority, registry), OutboxService(repository, authority, registry)


def _action(action_service: ActionService) -> dict[str, object]:
    candidate = action_service.propose_action(
        submitted_by="principal-outbox",
        owner_ref="principal-outbox",
        space_id="space-outbox",
        action_kind="shadow.action.send-notification",
        target_ref={"record_id": "target-outbox", "resource_kind": "notification"},
        typed_parameters={"channel": "test", "body": "hello"},
        data_classification="personal",
        side_effect_level="low",
        required_capabilities=["shadow.action.notify"],
        deadline="2099-01-01T00:00:00Z",
        secret_refs=[],
    )
    proposal = action_service.submit_proposal(candidate, idempotency_key="action-proposal")
    return action_service.accept_proposal(
        proposal_id=proposal["record_id"],
        proposal_expected_version=proposal["version"],
        principal_ref="principal-outbox",
        space_id="space-outbox",
        idempotency_key="action-accept",
    )["record"]


def _intent(outbox: OutboxService, action: dict[str, object], *, key: str = "outbox-key"):
    candidate = outbox.propose_intent(
        principal_ref="principal-outbox",
        space_id="space-outbox",
        action_ref={"record_id": action["record_id"], "version": action["version"]},
        target_ref={"record_id": "target-outbox", "resource_kind": "notification"},
        operation_kind="shadow.action.notify",
        capability="shadow.action.notify",
        delivery_class="reliable-side-effect",
        parameter_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        data_classification="personal",
        side_effect_level="low",
        deadline="2099-01-01T00:00:00Z",
        idempotency_key=key,
    )
    return outbox.create_intent(candidate)


def test_intent_is_persisted_before_delivery_and_replay_is_stable(tmp_path: Path) -> None:
    repository, actions, outbox = _services(tmp_path)
    action = _action(actions)
    created = _intent(outbox, action)
    intent_id = created["record"]["record_id"]
    assert created["record"]["typed_payload"]["lifecycle"] == "pending"

    leased = outbox.lease_intent(
        intent_id=intent_id,
        expected_version=1,
        principal_ref="principal-outbox",
        space_id="space-outbox",
        lease_owner="worker-1",
        lease_expires_at="2099-01-01T00:00:00Z",
        idempotency_key="lease-key",
    )
    adapter = DeterministicOutboxAdapter(outcome="delivered")
    result = outbox.record_delivery_result(
        intent_id=intent_id,
        expected_version=2,
        principal_ref="principal-outbox",
        space_id="space-outbox",
        result_payload=adapter.deliver(leased["record"]),
        idempotency_key="delivery-key",
    )
    replay = outbox.record_delivery_result(
        intent_id=intent_id,
        expected_version=2,
        principal_ref="principal-outbox",
        space_id="space-outbox",
        result_payload={
            "outcome": "delivered",
            "provider_ref": "deterministic-outbox-provider",
            "observed_at": "2026-08-22T08:01:00Z",
        },
        idempotency_key="delivery-key",
    )
    assert result["record"]["typed_payload"]["lifecycle"] == "delivered"
    assert replay["replayed"] is True
    assert replay["result"]["record_id"] == result["result"]["record_id"]
    assert repository.current_version(intent_id) == 3
    assert adapter.deliver_calls == 1


def test_unknown_requires_reconciliation_and_can_remain_unknown(tmp_path: Path) -> None:
    _, actions, outbox = _services(tmp_path)
    action = _action(actions)
    intent_id = _intent(outbox, action)["record"]["record_id"]
    leased = outbox.lease_intent(
        intent_id=intent_id, expected_version=1, principal_ref="principal-outbox", space_id="space-outbox",
        lease_owner="worker-1", lease_expires_at="2099-01-01T00:00:00Z", idempotency_key="lease-key",
    )
    adapter = DeterministicOutboxAdapter(outcome="unknown")
    uncertain = outbox.record_delivery_result(
        intent_id=intent_id, expected_version=2, principal_ref="principal-outbox", space_id="space-outbox",
        result_payload=adapter.deliver(leased["record"]), idempotency_key="delivery-key",
    )
    assert uncertain["record"]["typed_payload"]["lifecycle"] == "unknown"
    with pytest.raises(ShadowDomainError) as exc_info:
        outbox.lease_intent(
            intent_id=intent_id, expected_version=3, principal_ref="principal-outbox", space_id="space-outbox",
            lease_owner="worker-2", lease_expires_at="2099-01-01T00:00:00Z", idempotency_key="retry-key",
        )
    assert exc_info.value.error.code == "shadow.outbox.invalid-transition"
    reconciled = outbox.reconcile_unknown(
        intent_id=intent_id, expected_version=3, principal_ref="principal-outbox", space_id="space-outbox",
        reconciliation_payload={
            "outcome": "unknown", "provider_ref": "deterministic-outbox-provider",
            "evidence_refs": ["provider-query-1"], "observed_at": "2026-08-22T08:05:00Z",
        }, idempotency_key="reconcile-key",
    )
    assert reconciled["record"]["typed_payload"]["lifecycle"] == "unknown"


def test_outbox_boundary_capability_owner_and_store_failure(tmp_path: Path) -> None:
    repository, actions, outbox = _services(tmp_path)
    action = _action(actions)
    with pytest.raises(ShadowDomainError) as unsupported:
        outbox.propose_intent(
            principal_ref="principal-outbox", space_id="space-outbox",
            action_ref={"record_id": action["record_id"], "version": 1}, target_ref={"record_id": "target-outbox"},
            operation_kind="shadow.action.unknown", capability="shadow.action.unknown", delivery_class="reliable-side-effect",
            parameter_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", data_classification="personal",
            side_effect_level="low", deadline="2099-01-01T00:00:00Z", idempotency_key="unsupported",
        )
    assert unsupported.value.error.code == "shadow.outbox.capability-unsupported"
    with pytest.raises(ShadowDomainError) as unauthorized:
        outbox.propose_intent(
            principal_ref="other", space_id="space-outbox",
            action_ref={"record_id": action["record_id"], "version": 1}, target_ref={"record_id": "target-outbox"},
            operation_kind="shadow.action.notify", capability="shadow.action.notify", delivery_class="reliable-side-effect",
            parameter_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", data_classification="personal",
            side_effect_level="low", deadline="2099-01-01T00:00:00Z", idempotency_key="unauthorized",
        )
    assert unauthorized.value.error.code == "shadow.outbox.unauthorized"
    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as unavailable:
        _intent(outbox, action)
    assert unavailable.value.error.code == "shadow.repository.unavailable"


def test_outbox_is_service_boundary_only_no_public_route() -> None:
    app = create_app("sqlite://")
    paths = {route.path for route in app.routes}
    assert "/v1/outbox" not in paths
    assert hasattr(app.state, "outbox")
