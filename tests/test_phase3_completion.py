from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shadow_application import (
    DeterministicClock,
    DeterministicMigrationAdapter,
    DeterministicScheduleAdapter,
    IntegrityService,
    StateConditionAdmission,
    StateService,
    TaskService,
)
from shadow_kernel.admission import AdmissionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path: Path) -> tuple[SqliteCanonicalRepository, TaskService, StateService, AdmissionService]:
    repo = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'continuity.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repo, registry)
    return repo, TaskService(repo, authority, registry), StateService(repo, authority, registry), AdmissionService(repo, authority)


def _task_proposal(service: TaskService, *, operation: str = "create", **overrides: object):
    values: dict[str, object] = {
        "submitted_by": "principal-task",
        "owner_ref": "principal-task",
        "space_id": "space-task",
        "operation": operation,
        "task_key": "task-weekly-plan",
        "goal": "Prepare weekly plan",
        "completion_criteria": {"kind": "confirmed"},
    }
    values.update(overrides)
    return service.propose(**values)


def _accept(service: TaskService, proposal: dict[str, object], *, key: str):
    return service.accept_proposal(
        proposal_id=proposal["record_id"],
        proposal_expected_version=proposal["version"],
        principal_ref="principal-task",
        space_id="space-task",
        idempotency_key=key,
    )


def test_task_lifecycle_run_success_does_not_complete_and_restart_recovers(tmp_path: Path) -> None:
    repo, tasks, _, _ = _services(tmp_path)
    proposal = tasks.submit_proposal(_task_proposal(tasks), idempotency_key="task-proposal")
    accepted = _accept(tasks, proposal, key="task-accept")
    task_id = accepted["task_ref"]["record_id"]
    linked = tasks.link_run(
        task_id=task_id,
        expected_version=1,
        run_ref={"record_id": "run-1", "version": 1},
        principal_ref="principal-task",
        space_id="space-task",
        idempotency_key="task-run-link",
    )
    assert linked["typed_payload"]["lifecycle"] == "active"
    assert linked["typed_payload"]["run_refs"] == [{"record_id": "run-1", "version": 1}]

    waiting = tasks.submit_proposal(
        _task_proposal(tasks, operation="completion_pending", target_task_id=task_id, expected_version=2),
        idempotency_key="task-pending-proposal",
    )
    pending = _accept(tasks, waiting, key="task-pending-accept")
    assert pending["record"]["typed_payload"]["lifecycle"] == "completion_pending"
    complete = tasks.submit_proposal(
        _task_proposal(tasks, operation="complete", target_task_id=task_id, expected_version=3, result_ref={"record_id": "result-1", "version": 1}),
        idempotency_key="task-complete-proposal",
    )
    completed = _accept(tasks, complete, key="task-complete-accept")
    assert completed["record"]["typed_payload"]["lifecycle"] == "completed"

    restarted_registry = ContractRegistry(ROOT)
    restarted = TaskService(repo, CommitAuthority(repo, restarted_registry), restarted_registry)
    restored = restarted.get_task(task_id, "principal-task", "space-task")
    assert restored is not None
    assert restored["typed_payload"]["run_refs"] == [{"record_id": "run-1", "version": 1}]
    assert restored["typed_payload"]["lifecycle"] == "completed"


def test_checkpoint_atomicity_capability_and_replay(tmp_path: Path) -> None:
    _, tasks, _, _ = _services(tmp_path)
    proposal = tasks.submit_proposal(_task_proposal(tasks), idempotency_key="checkpoint-task")
    task_id = _accept(tasks, proposal, key="checkpoint-task-accept")["task_ref"]["record_id"]
    with pytest.raises(ShadowDomainError) as unsupported:
        tasks.create_checkpoint(
            task_id=task_id,
            expected_task_version=1,
            principal_ref="principal-task",
            space_id="space-task",
            checkpoint_kind="native",
            checkpoint_digest="sha256:" + "a" * 64,
            runtime_target_kind="shadow.test-runner",
            runtime_capabilities=[],
            artifact_refs=[],
            native_resume=False,
            idempotency_key="checkpoint-unsupported",
        )
    assert unsupported.value.error.code == "shadow.continuity.capability-unsupported"
    first = tasks.create_checkpoint(
        task_id=task_id,
        expected_task_version=1,
        principal_ref="principal-task",
        space_id="space-task",
        checkpoint_kind="semantic",
        checkpoint_digest="sha256:" + "b" * 64,
        runtime_target_kind="shadow.test-runner",
        runtime_capabilities=["shadow.execution.checkpoint"],
        artifact_refs=[],
        native_resume=False,
        idempotency_key="checkpoint-1",
    )
    replay = tasks.create_checkpoint(
        task_id=task_id,
        expected_task_version=1,
        principal_ref="principal-task",
        space_id="space-task",
        checkpoint_kind="semantic",
        checkpoint_digest="sha256:" + "b" * 64,
        runtime_target_kind="shadow.test-runner",
        runtime_capabilities=["shadow.execution.checkpoint"],
        artifact_refs=[],
        native_resume=False,
        idempotency_key="checkpoint-1",
    )
    assert first["checkpoint"]["record_id"] == replay["checkpoint"]["record_id"]
    assert replay["replayed"] is True
    assert len(replay["task"]["typed_payload"]["checkpoint_refs"]) == 1


def test_schedule_state_condition_reenters_admission(tmp_path: Path) -> None:
    _, _, states, admission = _services(tmp_path)
    state_proposal = states.submit_proposal(
        states.propose(
            submitted_by="principal-task", owner_ref="principal-task", space_id="space-task",
            operation="create", state_key="presence.home", value_schema_ref="schema:presence",
            proposed_value=True, evidence_refs=[], source_refs=["test"],
            observed_at="2026-08-22T08:00:00Z", expires_at="2099-08-22T00:00:00Z", source_status="available",
        ),
        idempotency_key="condition-state-proposal",
    )
    state = states.accept_proposal(
        proposal_id=state_proposal["record_id"], proposal_expected_version=1,
        principal_ref="principal-task", space_id="space-task", idempotency_key="condition-state-accept",
    )["record"]
    condition = StateConditionAdmission(states, admission, ContractRegistry(ROOT))
    result = condition.evaluate_and_admit(
        state_id=state["record_id"], expected_state_key="presence.home", expected_value=True,
        principal_ref="principal-task", space_id="space-task", request_type="shadow.state-trigger",
        endpoint_ref="endpoint-test", idempotency_key="condition-admission",
    )
    assert result is not None
    assert result.decision == "accepted"
    assert result.run is not None


def test_clock_schedule_migration_and_integrity_boundaries(tmp_path: Path) -> None:
    clock = DeterministicClock(datetime(2026, 8, 22, 8, tzinfo=UTC))
    adapter = DeterministicScheduleAdapter("schedule.daily")
    trigger = adapter.observe(schedule_key="schedule.daily", now=clock.now())
    ContractRegistry(ROOT).validate(trigger, "https://schemas.openshadow.dev/contracts/continuity/1.0.0#/$defs/TriggerObservation")
    assert trigger["condition_met"] is True
    assert clock.advance(60).endswith("Z")

    migration = DeterministicMigrationAdapter("schema:1", "schema:2")
    assert migration.migrate({"value": 1}, from_schema="schema:1", to_schema="schema:2") == {"value": 1}
    with pytest.raises(ShadowDomainError) as incompatible:
        migration.migrate({}, from_schema="schema:0", to_schema="schema:2")
    assert incompatible.value.error.code == "shadow.migration.incompatible"

    repo, _, _, _ = _services(tmp_path)
    record = {
        "record_id": "record-1", "version": 1, "owner_ref": "principal-task", "space_id": "space-task",
        "typed_payload": {"value": 1},
    }
    integrity = IntegrityService(ContractRegistry(ROOT))
    manifest = integrity.build_manifest([record], owner_ref="principal-task", space_id="space-task")
    assert integrity.verify_manifest([record], manifest, owner_ref="principal-task", space_id="space-task")
    tampered = dict(record, typed_payload={"value": 2})
    with pytest.raises(ShadowDomainError) as mismatch:
        integrity.verify_manifest([tampered], manifest, owner_ref="principal-task", space_id="space-task")
    assert mismatch.value.error.code == "shadow.integrity.digest-mismatch"
    assert repo.available


def test_task_api_and_checkpoint_route(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    client = TestClient(app)
    headers = {"X-Principal-Ref": "principal-api-task", "X-Space-Id": "space-api-task", "Idempotency-Key": "api-task-proposal"}
    body = {
        "input_type": "shadow.durable-task-proposal", "proposed_operation": "create",
        "task_key": "api-task", "goal": "Do API task", "completion_criteria": {"kind": "manual"},
    }
    response = client.post("/v1/proposals", json=body, headers=headers)
    assert response.status_code == 202, response.text
    proposal = response.json()["record"]
    accepted = client.post(
        f"/v1/proposals/{proposal['record_id']}/accept",
        headers={**headers, "Expected-Version": "1", "Idempotency-Key": "api-task-accept"},
    )
    assert accepted.status_code == 200, accepted.text
    task_id = accepted.json()["task_ref"]["record_id"]
    checkpoint = client.post(
        f"/v1/tasks/{task_id}/checkpoints",
        json={"checkpoint_kind": "semantic", "checkpoint_digest": "sha256:" + "c" * 64, "runtime_target_kind": "shadow.test-runner"},
        headers={**headers, "Expected-Version": "1", "Idempotency-Key": "api-checkpoint"},
    )
    assert checkpoint.status_code == 200, checkpoint.text
    task = client.get(f"/v1/tasks/{task_id}", headers={"X-Principal-Ref": "principal-api-task", "X-Space-Id": "space-api-task"})
    assert task.status_code == 200
    assert task.json()["record"]["typed_payload"]["checkpoint_refs"]
