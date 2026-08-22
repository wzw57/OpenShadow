from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shadow_adapters import DeterministicStateSourceAdapter
from shadow_application import StateService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path: Path) -> tuple[SqliteCanonicalRepository, StateService]:
    repository = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'state.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    return repository, StateService(repository, CommitAuthority(repository, registry), registry)


def _proposal(service: StateService, *, operation: str = "create", **overrides: object):
    values = {
        "submitted_by": "principal-state",
        "owner_ref": "principal-state",
        "space_id": "space-state",
        "operation": operation,
        "state_key": "presence.home",
        "value_schema_ref": "https://schemas.openshadow.dev/examples/presence/1.0.0",
        "proposed_value": {"present": True},
        "evidence_refs": [
            {
                "evidence_id": "evidence-state-test",
                "source_ref": "adapter:deterministic-state",
                "availability": "available",
                "observed_at": "2026-08-22T08:00:00Z",
            }
        ],
        "source_refs": ["adapter:deterministic-state"],
        "observed_at": "2026-08-22T08:00:00Z",
        "expires_at": "2099-08-22T08:00:00Z",
        "source_status": "available",
    }
    values.update(overrides)
    return service.propose(**values)


def _accept(service: StateService, proposal: dict[str, object], *, key: str = "accept-1"):
    return service.accept_proposal(
        proposal_id=proposal["record_id"],
        proposal_expected_version=proposal["version"],
        principal_ref="principal-state",
        space_id="space-state",
        idempotency_key=key,
    )


def test_state_create_read_list_and_restart(tmp_path: Path) -> None:
    repository, service = _services(tmp_path)
    proposal = service.submit_proposal(_proposal(service), idempotency_key="proposal-1")
    decision = _accept(service, proposal)
    state_id = decision["state_ref"]["record_id"]
    state = service.get_state(state_id, principal_ref="principal-state", space_id="space-state")

    assert state is not None
    assert state["version"] == 1
    assert state["typed_payload"]["state_key"] == "presence.home"
    assert state["typed_payload"]["freshness"] == "fresh"
    assert service.list_states(owner_ref="principal-state", space_id="space-state")[0]["record_id"] == state_id

    restarted = StateService(repository, CommitAuthority(repository, ContractRegistry(ROOT)), ContractRegistry(ROOT))
    restored = restarted.get_state(state_id, principal_ref="principal-state", space_id="space-state")
    assert restored is not None
    assert restored["typed_payload"]["expires_at"] == "2099-08-22T08:00:00Z"


def test_state_update_replay_and_expected_version_conflict(tmp_path: Path) -> None:
    _, service = _services(tmp_path)
    created = _accept(service, service.submit_proposal(_proposal(service), idempotency_key="p-create"))
    state_id = created["state_ref"]["record_id"]
    stale = _proposal(
        service,
        operation="update",
        target_state_id=state_id,
        expected_version=1,
        proposed_value={"present": True},
    )
    update = _proposal(
        service,
        operation="update",
        target_state_id=state_id,
        expected_version=1,
        proposed_value={"present": False},
    )
    proposal = service.submit_proposal(update, idempotency_key="p-update")
    first = _accept(service, proposal, key="accept-update")
    replay = service.accept_proposal(
        proposal_id=proposal["record_id"],
        proposal_expected_version=1,
        principal_ref="principal-state",
        space_id="space-state",
        idempotency_key="accept-update",
    )
    assert first["state_ref"] == replay["state_ref"]
    assert service.get_state(state_id)["version"] == 2

    stale_record = service.submit_proposal(stale, idempotency_key="p-stale")
    with pytest.raises(ShadowDomainError) as exc_info:
        _accept(service, stale_record, key="accept-stale")
    assert exc_info.value.error.code == "shadow.repository.expected-version-conflict"


def test_state_expiry_source_unavailable_and_owner_boundary(tmp_path: Path) -> None:
    _, service = _services(tmp_path)
    expired = _proposal(service, expires_at="2020-01-01T00:00:00Z")
    created = _accept(service, service.submit_proposal(expired, idempotency_key="p-expired"))
    state_id = created["state_ref"]["record_id"]
    assert service.get_state(state_id)["typed_payload"]["freshness"] == "stale"
    with pytest.raises(ShadowDomainError) as exc_info:
        service.get_state(state_id, principal_ref="other", space_id="space-state")
    assert exc_info.value.error.code == "shadow.state.owner-space-mismatch"

    unavailable = _proposal(
        service,
        state_key="calendar.next_event",
        source_status="unavailable",
        proposed_value={"title": "old"},
    )
    unavailable_record = _accept(
        service, service.submit_proposal(unavailable, idempotency_key="p-unavailable"), key="a-unavailable"
    )
    assert service.get_state(unavailable_record["state_ref"]["record_id"])["typed_payload"]["freshness"] == "stale"


def test_deleted_state_head_rejects_old_update(tmp_path: Path) -> None:
    _, service = _services(tmp_path)
    created = _accept(service, service.submit_proposal(_proposal(service), idempotency_key="p-delete-create"))
    state_id = created["state_ref"]["record_id"]
    old = _proposal(
        service,
        operation="update",
        target_state_id=state_id,
        expected_version=1,
    )
    delete = _proposal(
        service,
        operation="logical_delete",
        target_state_id=state_id,
        expected_version=1,
    )
    deleted = _accept(service, service.submit_proposal(delete, idempotency_key="p-delete"), key="a-delete")
    assert service.get_state(state_id)["record_state"] == "logically_deleted"
    assert service.list_states(owner_ref="principal-state", space_id="space-state") == []

    old_record = service.submit_proposal(old, idempotency_key="p-old")
    with pytest.raises(ShadowDomainError) as exc_info:
        _accept(service, old_record, key="a-old")
    assert exc_info.value.error.code == "shadow.state.head-not-active"
    assert deleted["state_ref"]["version"] == 2


def test_state_store_unavailable_does_not_commit(tmp_path: Path) -> None:
    repository, service = _services(tmp_path)
    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as exc_info:
        service.submit_proposal(_proposal(service), idempotency_key="p-outage")
    assert exc_info.value.error.code == "shadow.repository.unavailable"


def test_deterministic_state_source_only_returns_observation() -> None:
    observation = DeterministicStateSourceAdapter().observe(
        state_key="presence.home", owner_ref="principal-state", space_id="space-state"
    )
    assert observation["source_status"] == "available"
    assert "record_id" not in observation
    assert "commit_id" not in observation
    ContractRegistry(ROOT).validate(
        observation,
        "https://schemas.openshadow.dev/contracts/state/1.0.0#/$defs/Observation",
    )


def test_state_api_proposal_accept_and_reads_are_contract_aligned(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    client = TestClient(app)
    headers = {
        "X-Principal-Ref": "principal-api-state",
        "X-Space-Id": "space-api-state",
        "Idempotency-Key": "api-proposal-1",
    }
    body = {
        "input_type": "shadow.state-proposal",
        "proposed_operation": "create",
        "state_key": "presence.home",
        "value_schema_ref": "https://schemas.openshadow.dev/examples/presence/1.0.0",
        "proposed_value": {"present": True},
        "evidence_refs": [
            {
                "evidence_id": "api-evidence",
                "source_ref": "adapter:deterministic-state",
                "availability": "available",
                "observed_at": "2026-08-22T08:00:00Z",
            }
        ],
        "source_refs": ["adapter:deterministic-state"],
        "observed_at": "2026-08-22T08:00:00Z",
        "expires_at": "2099-08-22T00:00:00Z",
        "source_status": "available",
    }
    response = client.post("/v1/proposals", json=body, headers=headers)
    assert response.status_code == 202, response.text
    proposal = response.json()["record"]
    accepted = client.post(
        f"/v1/proposals/{proposal['record_id']}/accept",
        headers={**headers, "Expected-Version": "1", "Idempotency-Key": "api-accept-1"},
    )
    assert accepted.status_code == 200, accepted.text
    state_id = accepted.json()["state_ref"]["record_id"]
    state_response = client.get(
        f"/v1/states/{state_id}",
        headers={"X-Principal-Ref": "principal-api-state", "X-Space-Id": "space-api-state"},
    )
    assert state_response.status_code == 200
    assert state_response.json()["record"]["typed_payload"]["freshness"] == "fresh"
    assert client.get(
        "/v1/states", headers={"X-Principal-Ref": "principal-api-state", "X-Space-Id": "space-api-state"}
    ).json()["records"]
