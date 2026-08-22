from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from shadow_adapters import (
    DeterministicMemoryMaintenanceAdapter,
    DeterministicMemoryRecallAdapter,
)
from shadow_application import (
    MemoryMaintenanceRequest,
    MemoryMaintenanceService,
    MemoryRecallQuery,
    MemoryRecallService,
    MemoryService,
)
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(
    tmp_path: Path,
) -> tuple[SqliteCanonicalRepository, MemoryService, ContractRegistry]:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, MemoryService(repository, authority, registry), registry


def _create_memory(
    service: MemoryService,
    *,
    key: str,
    owner_ref: str = "principal-test",
    space_id: str = "space-test",
    text: str = "alpha preference",
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


def _query(text: str = "alpha") -> MemoryRecallQuery:
    return MemoryRecallQuery(
        principal_ref="principal-test",
        space_id="space-test",
        query_text=text,
        request_id=f"recall-{text}",
    )


def _maintenance_request(
    record: dict, *, principal_ref: str = "principal-test"
) -> MemoryMaintenanceRequest:
    return MemoryMaintenanceRequest(
        principal_ref=principal_ref,
        space_id="space-test",
        request_id="maintenance-1",
        targets=[{"record_id": record["record_id"], "version": record["version"]}],
        reason="quality-review",
    )


def test_recall_returns_only_canonical_active_heads(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    active = _create_memory(memories, key="recall-active", text="alpha preference")
    deleted = _create_memory(memories, key="recall-deleted", text="alpha deleted")
    memories.logical_delete(
        memory_id=deleted["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="delete-for-recall",
    )

    service = MemoryRecallService(repository, DeterministicMemoryRecallAdapter())
    result = service.recall(_query())

    assert result.result_state == "complete"
    assert [item.record_ref.record_id for item in result.items] == [active["record_id"]]
    assert result.items[0].record_ref.version == 1
    assert result.result_digest.startswith("sha256:")


def test_bounded_stale_recall_marks_historical_versions_explicitly(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="recall-history", text="alpha preference")
    candidate = memories.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "alpha preference corrected"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    corrected = memories.commit_correction(candidate, idempotency_key="recall-history-correction")
    query = _query("alpha")
    bounded = query.model_copy(update={"consistency": "bounded_stale", "limit": 10})

    result = MemoryRecallService(repository, DeterministicMemoryRecallAdapter()).recall(bounded)

    assert result.result_state == "stale"
    assert {
        item.record_ref.version
        for item in result.items
        if item.record_ref.record_id == original["record_id"]
    } == {1, corrected["version"]}


def test_recall_enforces_owner_space_and_explicit_stale_unavailable(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="recall-owner")
    service = MemoryRecallService(repository, DeterministicMemoryRecallAdapter())
    other = service.recall(
        MemoryRecallQuery(
            principal_ref="principal-other",
            space_id="space-other",
            query_text="alpha",
            request_id="other-owner",
        )
    )
    assert other.items == []

    stale = MemoryRecallService(
        repository,
        DeterministicMemoryRecallAdapter(result_state="stale"),
    ).recall(_query())
    assert stale.result_state == "stale"
    assert stale.items == []

    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as unavailable:
        service.recall(_query())
    assert unavailable.value.error.code == "shadow.memory.recall-unavailable"


def test_recall_rejects_adapter_item_outside_canonical_snapshot(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="recall-invalid")

    class InvalidAdapter:
        adapter_version = "invalid-1"

        def recall(self, query, snapshots):
            del query, snapshots
            return {
                "result_state": "complete",
                "items": [
                    {
                        "record_ref": {"record_id": "memory-not-active", "version": 1},
                        "match_kind": "invalid",
                    }
                ],
            }

    with pytest.raises(ShadowDomainError) as invalid:
        MemoryRecallService(repository, InvalidAdapter()).recall(_query())
    assert invalid.value.error.code == "shadow.memory.recall-invalid"


def test_recall_restart_uses_canonical_memory_as_authority(tmp_path: Path) -> None:
    database = tmp_path / "restart.db"
    repository = SqliteCanonicalRepository(database)
    registry = ContractRegistry(ROOT)
    memories = MemoryService(repository, CommitAuthority(repository, registry), registry)
    original = _create_memory(memories, key="recall-restart", text="restart alpha")
    first = MemoryRecallService(repository, DeterministicMemoryRecallAdapter()).recall(
        _query("restart")
    )

    restarted = SqliteCanonicalRepository(database)
    recovered = MemoryRecallService(restarted, DeterministicMemoryRecallAdapter()).recall(
        _query("restart")
    )

    assert len(first.items) == 1
    assert [item.record_ref.record_id for item in recovered.items] == [original["record_id"]]


def test_maintenance_enforces_owner_space_and_active_head(tmp_path: Path) -> None:
    repository, memories, registry = _services(tmp_path)
    owned = _create_memory(memories, key="maintenance-owned")
    other = _create_memory(
        memories,
        key="maintenance-other",
        owner_ref="principal-other",
        space_id="space-other",
    )
    service = MemoryMaintenanceService(
        repository,
        registry,
        DeterministicMemoryMaintenanceAdapter(),
    )
    with pytest.raises(ShadowDomainError) as unauthorized:
        service.maintain(_maintenance_request(other))
    assert unauthorized.value.error.code == "shadow.memory.owner-space-mismatch"

    memories.logical_delete(
        memory_id=owned["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="maintenance-delete",
    )
    with pytest.raises(ShadowDomainError) as deleted:
        service.maintain(_maintenance_request(owned))
    assert deleted.value.error.code == "shadow.memory.head-not-active"


def test_maintenance_returns_validated_proposals_without_committing(tmp_path: Path) -> None:
    repository, memories, registry = _services(tmp_path)
    original = _create_memory(memories, key="maintenance-target")
    proposal = {
        "proposed_operation": "correct",
        "targets": [{"memory_ref": {"record_id": original["record_id"]}, "expected_version": 1}],
        "memory_kind": "shadow.memory.preference",
        "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
        "proposed_content": {"text": "maintained"},
        "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        "evidence_refs": [],
        "source_refs": [],
        "source_dependency": "independent",
    }
    service = MemoryMaintenanceService(
        repository,
        registry,
        DeterministicMemoryMaintenanceAdapter(proposals=(proposal,)),
    )

    result = service.maintain(_maintenance_request(original))

    assert result.result_state == "complete"
    assert result.proposals == [proposal]
    assert result.proposal_digests[0].startswith("sha256:")
    assert result.result_digest.startswith("sha256:")
    assert repository.current_version(original["record_id"]) == 1


def test_maintenance_rejects_invalid_target_and_never_claims_unavailable_commit(
    tmp_path: Path,
) -> None:
    repository, memories, registry = _services(tmp_path)
    original = _create_memory(memories, key="maintenance-invalid")
    create_proposal = {
        "proposed_operation": "create",
        "targets": [],
        "memory_kind": "shadow.memory.preference",
        "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
        "proposed_content": {"text": "not allowed"},
        "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        "evidence_refs": [],
        "source_refs": [],
        "source_dependency": "independent",
    }
    service = MemoryMaintenanceService(
        repository,
        registry,
        DeterministicMemoryMaintenanceAdapter(proposals=(create_proposal,)),
    )
    with pytest.raises(ShadowDomainError) as invalid:
        service.maintain(_maintenance_request(original))
    assert invalid.value.error.code == "shadow.memory.maintenance-invalid"
    assert repository.current_version(original["record_id"]) == 1

    repository.set_available(False)
    unavailable_service = MemoryMaintenanceService(
        repository,
        registry,
        DeterministicMemoryMaintenanceAdapter(),
    )
    with pytest.raises(ShadowDomainError) as unavailable:
        unavailable_service.maintain(_maintenance_request(original))
    assert unavailable.value.error.code == "shadow.memory.maintenance-unavailable"


@pytest.mark.parametrize(
    ("relative_path", "model"),
    [
        ("recall/valid-memory-recall-query.json", MemoryRecallQuery),
        ("recall/valid-memory-maintenance-request.json", MemoryMaintenanceRequest),
    ],
)
def test_valid_recall_contract_fixtures(relative_path: str, model: type) -> None:
    payload = json.loads((ROOT / "contracts" / "fixtures" / relative_path).read_text())
    model.model_validate(payload)


def test_invalid_recall_contract_fixtures_are_rejected() -> None:
    invalid_query = json.loads(
        (ROOT / "contracts" / "fixtures" / "recall/invalid-memory-recall-query.json").read_text()
    )
    invalid_request = json.loads(
        (
            ROOT / "contracts" / "fixtures" / "recall/invalid-memory-maintenance-request.json"
        ).read_text()
    )
    with pytest.raises((ValueError, ValidationError)):
        MemoryRecallQuery.model_validate(invalid_query)
    with pytest.raises((ValueError, ValidationError)):
        MemoryMaintenanceRequest.model_validate(invalid_request)
