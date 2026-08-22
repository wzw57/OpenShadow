from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shadow_adapters import DeterministicActionProvider
from shadow_application import ActionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path: Path) -> tuple[SqliteCanonicalRepository, ActionService]:
    repository = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'action.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    return repository, ActionService(repository, CommitAuthority(repository, registry), registry)


def _candidate(service: ActionService, *, side_effect_level: str = "low", **overrides: object):
    values: dict[str, object] = {
        "submitted_by": "principal-action",
        "owner_ref": "principal-action",
        "space_id": "space-action",
        "action_kind": "shadow.action.send-notification",
        "target_ref": {"record_id": "target-1", "resource_kind": "notification"},
        "typed_parameters": {"channel": "test", "body": "hello"},
        "data_classification": "personal",
        "side_effect_level": side_effect_level,
        "required_capabilities": ["shadow.action.notify"],
        "deadline": "2099-01-01T00:00:00Z",
        "secret_refs": [],
        "provider_target_kind": "shadow.deterministic-action",
    }
    values.update(overrides)
    return service.propose_action(**values)


def _accept(service: ActionService, proposal: dict[str, object], *, key: str, principal: str = "principal-action", space: str = "space-action"):
    return service.accept_proposal(
        proposal_id=proposal["record_id"],
        proposal_expected_version=proposal["version"],
        principal_ref=principal,
        space_id=space,
        idempotency_key=key,
    )


def test_low_risk_action_is_persisted_before_provider_and_replay_is_stable(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    proposal = service.submit_proposal(_candidate(service), idempotency_key="action-proposal")
    accepted = _accept(service, proposal, key="action-accept")
    action_id = accepted["action_ref"]["record_id"]
    assert accepted["record"]["typed_payload"]["lifecycle"] == "approved"

    executing = service.begin_execution(
        action_id=action_id,
        expected_version=1,
        principal_ref="principal-action",
        space_id="space-action",
        idempotency_key="action-execute",
    )
    assert executing["record"]["typed_payload"]["lifecycle"] == "executing"
    provider = DeterministicActionProvider(outcome="succeeded")
    result = provider.execute(executing["record"])
    completed = service.record_provider_result(
        action_id=action_id,
        expected_version=2,
        principal_ref="principal-action",
        space_id="space-action",
        idempotency_key="action-result",
        **result,
    )
    replay = service.record_provider_result(
        action_id=action_id,
        expected_version=2,
        principal_ref="principal-action",
        space_id="space-action",
        idempotency_key="action-result",
        **result,
    )
    assert completed["record"]["typed_payload"]["lifecycle"] == "succeeded"
    assert replay["replayed"] is True
    assert replay["result"]["record_id"] == completed["result"]["record_id"]
    assert repository.current_version(action_id) == 3

    restarted = ActionService(repository, CommitAuthority(repository, ContractRegistry(ROOT)), ContractRegistry(ROOT))
    assert restarted.get_action(action_id, "principal-action", "space-action")["typed_payload"]["lifecycle"] == "succeeded"


def test_medium_action_requires_approval_and_reject_is_a_durable_result(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    proposal = service.submit_proposal(_candidate(service, side_effect_level="medium"), idempotency_key="medium-proposal")
    accepted = _accept(service, proposal, key="medium-accept")
    action_id = accepted["action_ref"]["record_id"]
    assert accepted["record"]["typed_payload"]["lifecycle"] == "approval_required"
    approval = service.propose_approval(
        submitted_by="principal-action",
        owner_ref="principal-action",
        space_id="space-action",
        action_id=action_id,
        expected_version=1,
        approver_ref="principal-action",
        decision="approved",
        evidence_refs=[{"record_id": "approval-evidence"}],
    )
    approval_record = service.submit_proposal(approval, idempotency_key="approval-proposal")
    approved = _accept(service, approval_record, key="approval-accept")
    assert approved["record"]["typed_payload"]["lifecycle"] == "approved"

    rejected_candidate = _candidate(service, side_effect_level="medium", action_kind="shadow.action.second")
    rejected_proposal = service.submit_proposal(rejected_candidate, idempotency_key="reject-proposal")
    rejected = _accept(service, rejected_proposal, key="reject-accept")
    rejected_action_id = rejected["action_ref"]["record_id"]
    approval = service.propose_approval(
        submitted_by="principal-action", owner_ref="principal-action", space_id="space-action",
        action_id=rejected_action_id, expected_version=1, approver_ref="principal-action",
        decision="rejected", evidence_refs=[{"record_id": "approval-evidence-2"}],
    )
    approval_record = service.submit_proposal(approval, idempotency_key="reject-approval-proposal")
    rejected_result = _accept(service, approval_record, key="reject-approval-accept")
    assert rejected_result["record"]["typed_payload"]["lifecycle"] == "failed"


def test_policy_capability_and_boundary_rejections(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    high = service.submit_proposal(_candidate(service, side_effect_level="high"), idempotency_key="high-proposal")
    with pytest.raises(ShadowDomainError) as denied:
        _accept(service, high, key="high-accept")
    assert denied.value.error.code == "shadow.action.policy-denied"

    unknown = service.submit_proposal(_candidate(service, required_capabilities=["shadow.action.unknown"]), idempotency_key="unknown-proposal")
    with pytest.raises(ShadowDomainError) as unsupported:
        _accept(service, unknown, key="unknown-accept")
    assert unsupported.value.error.code == "shadow.action.capability-unsupported"

    proposal = service.submit_proposal(_candidate(service), idempotency_key="boundary-proposal")
    accepted = _accept(service, proposal, key="boundary-accept")
    with pytest.raises(ShadowDomainError) as unauthorized:
        service.get_action(accepted["action_ref"]["record_id"], "principal-other", "space-action")
    assert unauthorized.value.error.code == "shadow.action.unauthorized"


def test_unknown_outcome_requires_evidence_and_cannot_be_reexecuted(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    proposal = service.submit_proposal(_candidate(service), idempotency_key="unknown-action-proposal")
    action_id = _accept(service, proposal, key="unknown-action-accept")["action_ref"]["record_id"]
    service.begin_execution(
        action_id=action_id, expected_version=1, principal_ref="principal-action", space_id="space-action", idempotency_key="unknown-execute",
    )
    unknown = service.record_provider_result(
        action_id=action_id, expected_version=2, principal_ref="principal-action", space_id="space-action",
        outcome="unknown", unknown_reason="transport uncertain", external_ref="provider-1",
        observed_at="2026-08-22T08:00:00Z", idempotency_key="unknown-result",
    )
    assert unknown["record"]["typed_payload"]["lifecycle"] == "unknown"
    with pytest.raises(ShadowDomainError) as blocked:
        service.begin_execution(
            action_id=action_id, expected_version=3, principal_ref="principal-action", space_id="space-action", idempotency_key="unknown-retry",
        )
    assert blocked.value.error.code == "shadow.action.invalid-transition"
    reconciled = service.reconcile_unknown(
        action_id=action_id, expected_version=3, principal_ref="principal-action", space_id="space-action",
        outcome="succeeded", evidence_refs=[{"record_id": "provider-evidence"}], observed_at="2026-08-22T08:05:00Z",
        external_ref="provider-1", idempotency_key="reconcile-success",
    )
    assert reconciled["record"]["typed_payload"]["lifecycle"] == "succeeded"


def test_action_api_uses_generic_proposals_and_owner_space_queries(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    client = TestClient(app)
    headers = {"X-Principal-Ref": "principal-api-action", "X-Space-Id": "space-api-action", "Idempotency-Key": "api-action-proposal"}
    body = {
        "input_type": "shadow.action-proposal", "proposed_operation": "create",
        "action_kind": "shadow.action.send-notification", "target_ref": {"record_id": "target-api"},
        "typed_parameters": {"channel": "test", "body": "hello"}, "data_classification": "personal",
        "side_effect_level": "low", "required_capabilities": ["shadow.action.notify"],
        "deadline": "2099-01-01T00:00:00Z", "secret_refs": [],
    }
    submitted = client.post("/v1/proposals", json=body, headers=headers)
    assert submitted.status_code == 202, submitted.text
    proposal = submitted.json()["record"]
    accepted = client.post(
        f"/v1/proposals/{proposal['record_id']}/accept",
        headers={**headers, "Expected-Version": "1", "Idempotency-Key": "api-action-accept"},
    )
    assert accepted.status_code == 200, accepted.text
    action_id = accepted.json()["action_ref"]["record_id"]
    listed = client.get("/v1/actions", headers={"X-Principal-Ref": "principal-api-action", "X-Space-Id": "space-api-action"})
    assert listed.status_code == 200
    assert listed.json()["records"][0]["record_id"] == action_id
    foreign = client.get(f"/v1/actions/{action_id}", headers={"X-Principal-Ref": "principal-other", "X-Space-Id": "space-api-action"})
    assert foreign.status_code == 403
