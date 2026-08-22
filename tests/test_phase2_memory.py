from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shadow_application import MemoryService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path: Path) -> tuple[SqliteCanonicalRepository, MemoryService]:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, MemoryService(repository, authority, registry)


def _create_memory(
    service: MemoryService,
    *,
    key: str,
    owner_ref: str = "principal-test",
    space_id: str = "space-test",
    text: str = "original",
) -> dict:
    candidate = service.propose_create(
        submitted_by=owner_ref,
        owner_ref=owner_ref,
        space_id=space_id,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": text},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    return service.commit_candidate(candidate, idempotency_key=key)


def _target(record: dict, version: int | None = None) -> dict:
    return {
        "memory_ref": {"record_id": record["record_id"]},
        "expected_version": version or record["version"],
    }


def test_memory_correction_preserves_stable_id_and_history(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    original = _create_memory(service, key="create-correction")
    candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "corrected"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    corrected = service.commit_correction(candidate, idempotency_key="correction-1")

    assert corrected["record_id"] == original["record_id"]
    assert corrected["version"] == 2
    assert corrected["typed_payload"]["typed_content"] == {"text": "corrected"}
    assert corrected["typed_payload"]["supersedes_version"] == 1
    assert repository.get(original["record_id"], 1) == original


def test_memory_correction_replay_does_not_create_a_new_version(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    original = _create_memory(service, key="create-replay")
    candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "replayed correction"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    first = service.commit_correction(candidate, idempotency_key="correction-replay")
    replay = service.commit_correction(candidate, idempotency_key="correction-replay")

    assert replay == first
    assert repository.current_version(original["record_id"]) == 2


def test_memory_merge_is_atomic_and_supersedes_all_inputs(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = _create_memory(service, key="create-merge-1", text="one")
    second = _create_memory(service, key="create-merge-2", text="two")
    candidate = service.propose_merge(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        targets=[_target(first), _target(second)],
        memory_kind="shadow.memory.fact",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "merged"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    merged = service.commit_merge(candidate, idempotency_key="merge-1")

    assert merged["version"] == 1
    assert {
        (ref["record_id"], ref["version"])
        for ref in merged["typed_payload"]["supersedes_memory_refs"]
    } == {(first["record_id"], 1), (second["record_id"], 1)}
    assert repository.get(first["record_id"])["typed_payload"]["memory_state"] == "superseded"
    assert repository.get(second["record_id"])["typed_payload"]["memory_state"] == "superseded"
    assert [record["record_id"] for record in service.list_memories()] == [merged["record_id"]]


def test_memory_merge_replay_does_not_create_additional_versions(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = _create_memory(service, key="create-merge-replay-1", text="one")
    second = _create_memory(service, key="create-merge-replay-2", text="two")
    candidate = service.propose_merge(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        targets=[_target(first), _target(second)],
        memory_kind="shadow.memory.fact",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "merged replay"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )

    first_result = service.commit_merge(candidate, idempotency_key="merge-replay")
    replay = service.commit_merge(candidate, idempotency_key="merge-replay")

    assert replay == first_result
    assert repository.current_version(first["record_id"]) == 2
    assert repository.current_version(second["record_id"]) == 2
    assert repository.current_version(first_result["record_id"]) == 1


def test_memory_merge_conflict_leaves_other_targets_and_new_memory_unchanged(
    tmp_path: Path,
) -> None:
    repository, service = _service(tmp_path)
    first = _create_memory(service, key="create-race-1")
    second = _create_memory(service, key="create-race-2")
    candidate = service.propose_merge(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        targets=[_target(first), _target(second)],
        memory_kind="shadow.memory.fact",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "race"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    before_ids = {
        record["record_id"]
        for record in repository.query(
            record_types={"shadow.profile.memory"},
            record_states={"active", "logically_deleted", "erased"},
            limit=100,
        )
    }
    correction = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=first["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "changed before merge"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    service.commit_correction(correction, idempotency_key="race-correction")

    with pytest.raises(ShadowDomainError) as failure:
        service.commit_merge(candidate, idempotency_key="merge-race")
    assert failure.value.error.code == "shadow.repository.expected-version-conflict"
    after_ids = {
        record["record_id"]
        for record in repository.query(
            record_types={"shadow.profile.memory"},
            record_states={"active", "logically_deleted", "erased"},
            limit=100,
        )
    }
    assert after_ids == before_ids
    assert repository.current_version(second["record_id"]) == 1
    assert repository.get(second["record_id"])["typed_payload"]["memory_state"] == "active"


def test_logical_delete_hides_head_and_rejects_resurrection(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    original = _create_memory(service, key="create-delete")
    stale_candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "resurrected"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    deleted = service.logical_delete(
        memory_id=original["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="delete-1",
    )

    assert deleted["record_state"] == "logically_deleted"
    assert deleted["typed_payload"]["memory_state"] == "active"
    assert service.list_memories() == []
    replayed = service.logical_delete(
        memory_id=original["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="delete-1",
    )
    assert replayed == deleted
    assert repository.current_version(original["record_id"]) == 2
    with pytest.raises(ShadowDomainError) as failure:
        service.logical_delete(
            memory_id=original["record_id"],
            expected_version=2,
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            idempotency_key="delete-again",
        )
    assert failure.value.error.code == "shadow.memory.head-not-active"

    with pytest.raises(ShadowDomainError) as stale_failure:
        service.commit_correction(stale_candidate, idempotency_key="stale-correction")
    assert stale_failure.value.error.code == "shadow.repository.expected-version-conflict"
    assert repository.get(original["record_id"])["record_state"] == "logically_deleted"

    with pytest.raises(ShadowDomainError) as deleted_head:
        service.propose_correction(
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            memory_id=original["record_id"],
            expected_version=2,
            memory_kind="shadow.memory.preference",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "resurrected again"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        )
    assert deleted_head.value.error.code == "shadow.memory.head-not-active"


def test_memory_write_checks_owner_and_store_availability(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    original = _create_memory(service, key="create-boundary")
    with pytest.raises(ShadowDomainError) as unauthorized:
        service.propose_correction(
            submitted_by="principal-other",
            owner_ref="principal-other",
            space_id="space-test",
            memory_id=original["record_id"],
            expected_version=1,
            memory_kind="shadow.memory.preference",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "not allowed"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        )
    assert unauthorized.value.error.code == "shadow.memory.owner-space-mismatch"

    candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "store unavailable"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as unavailable:
        service.commit_correction(candidate, idempotency_key="unavailable-correction")
    assert unavailable.value.error.code == "shadow.repository.unavailable"
    assert repository.available is False


def test_memory_lifecycle_rejects_missing_and_cross_owner_targets(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    with pytest.raises(ShadowDomainError) as missing:
        service.propose_correction(
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            memory_id="memory-missing",
            expected_version=1,
            memory_kind="shadow.memory.preference",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "missing"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        )
    assert missing.value.error.code == "shadow.memory.not-found"

    owned = _create_memory(service, key="create-owned")
    other = _create_memory(
        service,
        key="create-other-owner",
        owner_ref="principal-other",
        space_id="space-other",
    )
    with pytest.raises(ShadowDomainError) as cross_owner:
        service.propose_merge(
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            targets=[_target(owned), _target(other)],
            memory_kind="shadow.memory.fact",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "cross owner"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        )
    assert cross_owner.value.error.code == "shadow.memory.owner-space-mismatch"

    candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=owned["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "first"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    first = service.commit_correction(candidate, idempotency_key="correction-digest")
    assert first["version"] == 2
    different = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=owned["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "different"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    with pytest.raises(ShadowDomainError) as mismatch:
        service.commit_correction(different, idempotency_key="correction-digest")
    assert mismatch.value.error.code == "shadow.repository.idempotency-mismatch"


def test_memory_restart_recovers_corrected_and_deleted_heads(tmp_path: Path) -> None:
    database = tmp_path / "shadow.db"
    repository = SqliteCanonicalRepository(database)
    service = MemoryService(
        repository, CommitAuthority(repository, ContractRegistry(ROOT)), ContractRegistry(ROOT)
    )
    original = _create_memory(service, key="create-restart")
    candidate = service.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "restart corrected"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    service.commit_correction(candidate, idempotency_key="restart-correction")
    service.logical_delete(
        memory_id=original["record_id"],
        expected_version=2,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="restart-delete",
    )

    restarted = SqliteCanonicalRepository(database)
    recovered = restarted.get(original["record_id"])
    assert recovered and recovered["version"] == 3
    assert recovered["record_state"] == "logically_deleted"
    assert (
        MemoryService(
            restarted,
            CommitAuthority(restarted, ContractRegistry(ROOT)),
            ContractRegistry(ROOT),
        ).list_memories()
        == []
    )


def test_memory_lifecycle_api_uses_expected_version_and_write_boundaries() -> None:
    app = create_app("sqlite://")
    client = TestClient(app)
    headers = {
        "Idempotency-Key": "api-memory-create",
        "X-Principal-Ref": "principal-api",
        "X-Space-Id": "space-api",
    }
    created = client.post(
        "/v1/memories",
        json={
            "memory_kind": "shadow.memory.preference",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "api original"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        },
        headers=headers,
    )
    assert created.status_code == 201
    memory_id = created.json()["record"]["record_id"]

    correction_headers = {
        "Idempotency-Key": "api-memory-correction",
        "Expected-Version": "1",
        "X-Principal-Ref": "principal-api",
        "X-Space-Id": "space-api",
    }
    corrected = client.post(
        f"/v1/memories/{memory_id}/corrections",
        json={
            "memory_kind": "shadow.memory.preference",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "api corrected"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        },
        headers=correction_headers,
    )
    assert corrected.status_code == 200
    assert corrected.json()["record"]["version"] == 2
    assert corrected.json()["record"]["typed_payload"]["supersedes_version"] == 1
    replay = client.post(
        f"/v1/memories/{memory_id}/corrections",
        json={
            "memory_kind": "shadow.memory.preference",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "api corrected"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        },
        headers=correction_headers,
    )
    assert replay.status_code == 200
    assert replay.json() == corrected.json()

    deleted = client.delete(
        f"/v1/memories/{memory_id}",
        headers={
            "Idempotency-Key": "api-memory-delete",
            "Expected-Version": "2",
            "X-Principal-Ref": "principal-api",
            "X-Space-Id": "space-api",
        },
    )
    assert deleted.status_code == 202
    assert deleted.json()["record"]["record_state"] == "logically_deleted"
    assert (
        client.get(
            "/v1/memories", headers={"X-Principal-Ref": "principal-api", "X-Space-Id": "space-api"}
        ).json()["records"]
        == []
    )

    unauthorized = client.post(
        f"/v1/memories/{memory_id}/corrections",
        json={
            "memory_kind": "shadow.memory.preference",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "not allowed"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        },
        headers={
            "Idempotency-Key": "api-memory-unauthorized",
            "Expected-Version": "1",
            "X-Principal-Ref": "principal-other",
            "X-Space-Id": "space-api",
        },
    )
    assert unauthorized.status_code == 403
    assert unauthorized.json()["code"] == "shadow.memory.owner-space-mismatch"
