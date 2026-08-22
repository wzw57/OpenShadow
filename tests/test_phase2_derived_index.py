from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from shadow_adapters import DeterministicMemoryIndexAdapter
from shadow_application import (
    MemoryIndexEntry,
    MemoryIndexRebuildRequest,
    MemoryIndexRebuildResult,
    MemoryIndexRebuildService,
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


def _request(
    *,
    request_id: str = "index-rebuild-1",
    principal_ref: str = "principal-test",
    space_id: str = "space-test",
    expected_snapshot_digest: str | None = None,
) -> MemoryIndexRebuildRequest:
    return MemoryIndexRebuildRequest(
        principal_ref=principal_ref,
        space_id=space_id,
        rebuild_request_id=request_id,
        index_revision="deterministic-v1",
        index_schema_ref="https://schemas.openshadow.dev/index/memory/1.0.0",
        expected_snapshot_digest=expected_snapshot_digest,
    )


def test_index_rebuild_filters_deleted_heads_and_is_deterministic(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    active = _create_memory(memories, key="index-active")
    deleted = _create_memory(memories, key="index-deleted", text="must disappear")
    memories.logical_delete(
        memory_id=deleted["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="index-delete",
    )
    adapter = DeterministicMemoryIndexAdapter()
    service = MemoryIndexRebuildService(repository, adapter)

    first = service.rebuild(_request())
    replay = service.rebuild(_request())

    assert first.result_state == "complete"
    assert first.published is True
    assert first.replayed is False
    assert replay.replayed is True
    assert replay.result_digest == first.result_digest
    assert replay.snapshot_digest == first.snapshot_digest
    assert [entry.record_ref.record_id for entry in first.entries] == [active["record_id"]]
    assert len(adapter.published) == 1


def test_index_entries_are_derived_only_and_ordered(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    second = _create_memory(memories, key="index-b", text="beta")
    first = _create_memory(memories, key="index-a", text="alpha")

    result = MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(
        _request()
    )

    assert [entry.record_ref.record_id for entry in result.entries] == sorted(
        [first["record_id"], second["record_id"]]
    )
    assert all("typed_content" not in entry.derived_fields for entry in result.entries)
    assert result.entry_digests == [
        entry_digest for entry_digest in result.entry_digests if entry_digest.startswith("sha256:")
    ]


def test_index_rebuild_isolated_by_owner_and_space(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    owned = _create_memory(memories, key="index-owned")
    _create_memory(
        memories,
        key="index-other",
        owner_ref="principal-other",
        space_id="space-other",
    )

    result = MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(
        _request()
    )

    assert [entry.record_ref.record_id for entry in result.entries] == [owned["record_id"]]
    assert all(entry.owner_ref == "principal-test" for entry in result.entries)
    assert all(entry.space_id == "space-test" for entry in result.entries)


def test_index_rebuild_expected_snapshot_mismatch_is_stale(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="index-stale")
    adapter = DeterministicMemoryIndexAdapter()

    result = MemoryIndexRebuildService(repository, adapter).rebuild(
        _request(expected_snapshot_digest="sha256:caller-expected")
    )

    assert result.result_state == "stale"
    assert result.published is False
    assert result.failure_detail["code"] == "shadow.memory.index-stale"
    assert adapter.published == {}


def test_index_rebuild_detects_concurrent_canonical_change_before_publish(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    target = _create_memory(memories, key="index-cas")

    class MutatingAdapter(DeterministicMemoryIndexAdapter):
        def stage(self, request, snapshots, snapshot_digest):
            artifact = super().stage(request, snapshots, snapshot_digest)
            memories.logical_delete(
                memory_id=target["record_id"],
                expected_version=1,
                submitted_by="principal-test",
                owner_ref="principal-test",
                space_id="space-test",
                idempotency_key="index-cas-delete",
            )
            return artifact

    adapter = MutatingAdapter()
    result = MemoryIndexRebuildService(repository, adapter).rebuild(_request())

    assert result.result_state == "stale"
    assert result.published is False
    assert result.failure_detail["code"] == "shadow.memory.index-stale"
    assert adapter.published == {}
    assert not adapter._staged


def test_index_rebuild_replay_conflict_for_new_snapshot(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="index-replay-a")
    adapter = DeterministicMemoryIndexAdapter()
    service = MemoryIndexRebuildService(repository, adapter)
    service.rebuild(_request(request_id="replay-key"))
    _create_memory(memories, key="index-replay-b")

    with pytest.raises(ShadowDomainError) as conflict:
        service.rebuild(_request(request_id="replay-key"))

    assert conflict.value.error.code == "shadow.memory.index-replay-conflict"
    assert len(adapter.published) == 1


def test_index_rebuild_rejects_invalid_staging_entry_without_publish(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="index-invalid-entry")

    class InvalidAdapter(DeterministicMemoryIndexAdapter):
        def stage(self, request, snapshots, snapshot_digest):
            artifact = super().stage(request, snapshots, snapshot_digest)
            invalid = artifact.model_dump(mode="json")
            invalid["entries"][0]["record_ref"] = {"record_id": "not-active", "version": 1}
            invalid["entry_digests"] = []
            return invalid

    adapter = InvalidAdapter()
    with pytest.raises(ShadowDomainError) as invalid:
        MemoryIndexRebuildService(repository, adapter).rebuild(_request())

    assert invalid.value.error.code == "shadow.memory.index-invalid"
    assert adapter.published == {}


def test_index_rebuild_unavailable_does_not_claim_success(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    _create_memory(memories, key="index-unavailable")
    adapter = DeterministicMemoryIndexAdapter(result_state="unavailable")
    service = MemoryIndexRebuildService(repository, adapter)

    with pytest.raises(ShadowDomainError) as unavailable:
        service.rebuild(_request())

    assert unavailable.value.error.code == "shadow.memory.index-unavailable"
    assert adapter.published == {}
    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as store_unavailable:
        MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(_request())
    assert store_unavailable.value.error.code == "shadow.memory.index-unavailable"


def test_deleted_memory_cannot_resurrect_into_index(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    target = _create_memory(memories, key="index-resurrection")
    memories.logical_delete(
        memory_id=target["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="index-resurrection-delete",
    )

    result = MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(
        _request()
    )

    assert result.entries == []
    assert result.entry_count == 0


def test_index_restart_rebuilds_from_canonical_snapshot(tmp_path: Path) -> None:
    database = tmp_path / "restart.db"
    repository = SqliteCanonicalRepository(database)
    registry = ContractRegistry(ROOT)
    memories = MemoryService(repository, CommitAuthority(repository, registry), registry)
    created = _create_memory(memories, key="index-restart", text="restart")
    first = MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(
        _request(request_id="restart-first")
    )

    restarted = SqliteCanonicalRepository(database)
    recovered = MemoryIndexRebuildService(
        restarted, DeterministicMemoryIndexAdapter()
    ).rebuild(_request(request_id="restart-second"))

    assert [entry.record_ref.record_id for entry in recovered.entries] == [created["record_id"]]
    assert recovered.snapshot_digest == first.snapshot_digest
    assert recovered.result_digest == first.result_digest


@pytest.mark.parametrize(
    ("relative_path", "model"),
    [
        ("index/valid-memory-index-rebuild-request.json", MemoryIndexRebuildRequest),
        ("index/valid-memory-index-entry.json", MemoryIndexEntry),
        ("index/valid-memory-index-result.json", MemoryIndexRebuildResult),
    ],
)
def test_valid_index_contract_fixtures(relative_path: str, model: type) -> None:
    payload = json.loads((ROOT / "contracts" / "fixtures" / relative_path).read_text())
    model.model_validate(payload)


def test_invalid_index_contract_fixtures_are_rejected() -> None:
    invalid_request = json.loads(
        (ROOT / "contracts" / "fixtures" / "index/invalid-memory-index-rebuild-request.json").read_text()
    )
    invalid_entry = json.loads(
        (ROOT / "contracts" / "fixtures" / "index/invalid-memory-index-entry.json").read_text()
    )
    with pytest.raises((ValueError, ValidationError)):
        MemoryIndexRebuildRequest.model_validate(invalid_request)
    with pytest.raises((ValueError, ValidationError)):
        MemoryIndexEntry.model_validate(invalid_entry)
