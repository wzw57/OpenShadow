from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from shadow_application import (
    MemoryService,
    PortableImportRequest,
    PortableImportService,
)
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository, build_export_bundle

ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path: Path) -> tuple[SqliteCanonicalRepository, MemoryService, PortableImportService]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    memories = MemoryService(repository, authority, registry)
    return repository, memories, PortableImportService(repository, authority, registry)


def _create_memory(
    service: MemoryService,
    *,
    key: str,
    owner_ref: str = "principal-test",
    space_id: str = "space-test",
    text: str = "portable memory",
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
    import_id: str = "import-1",
    key: str = "import-key-1",
    principal_ref: str = "principal-test",
    space_id: str = "space-test",
    identity_mode: str = "strict",
) -> PortableImportRequest:
    return PortableImportRequest(
        principal_ref=principal_ref,
        space_id=space_id,
        import_id=import_id,
        identity_mode=identity_mode,
        idempotency_key=key,
    )


def _bundle(records: list[dict]) -> dict:
    return build_export_bundle(records, export_id="portable-fixture")


def test_portable_restore_validates_and_commits_selected_snapshot(tmp_path: Path) -> None:
    source_repo, source_memories, _ = _services(tmp_path / "source")
    record = _create_memory(source_memories, key="portable-source")
    bundle = _bundle([record])

    target_repo, _, target_import = _services(tmp_path / "target")
    result = target_import.restore(_request(), bundle)

    assert result.result_state == "committed"
    assert result.source_manifest_digest == bundle["manifest_digest"]
    assert [item.action for item in result.imported] == ["imported"]
    restored = target_repo.get(record["record_id"])
    assert restored is not None
    assert restored["typed_payload"] == record["typed_payload"]
    assert source_repo.get(record["record_id"]) == record


def test_portable_restore_rejects_tampering_before_any_write(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    record = _create_memory(source_memories, key="portable-tamper")
    bundle = _bundle([record])
    bundle["records"][0]["typed_payload"]["typed_content"] = {"text": "tampered"}

    target_repo, _, target_import = _services(tmp_path / "target")
    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(_request(), bundle)
    assert exc_info.value.error.code == "shadow.portable-import.invalid-bundle"
    assert target_repo.query(record_types={"shadow.profile.memory"}) == []


def test_portable_restore_rejects_duplicate_record_ids_in_snapshot(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    first = _create_memory(source_memories, key="portable-duplicate")
    candidate = source_memories.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=first["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "version two"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    second = source_memories.commit_correction(candidate, idempotency_key="portable-duplicate-v2")
    bundle = _bundle([first, second])
    _, _, target_import = _services(tmp_path / "target")

    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(_request(), bundle)
    assert exc_info.value.error.code == "shadow.portable-import.invalid-bundle"


def test_portable_restore_strict_owner_boundary_and_explicit_remap(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    source = _create_memory(
        source_memories,
        key="portable-remap",
        owner_ref="principal-source",
        space_id="space-source",
    )
    bundle = _bundle([source])
    _, _, target_import = _services(tmp_path / "target")

    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(_request(), bundle)
    assert exc_info.value.error.code == "shadow.portable-import.owner-space-mismatch"

    remapped = target_import.restore(
        _request(identity_mode="remap_to_target", key="portable-remap-target"), bundle
    )
    assert remapped.result_state == "committed"
    target_repo = target_import.repository
    restored = target_repo.get(source["record_id"])
    assert restored["owner_ref"] == "principal-test"
    assert restored["space_id"] == "space-test"
    assert restored["record_id"] == source["record_id"]


def test_portable_restore_is_idempotent_and_no_change_is_explicit(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    record = _create_memory(source_memories, key="portable-idempotent")
    bundle = _bundle([record])
    target_repo, _, target_import = _services(tmp_path / "target")
    request = _request(key="portable-idempotent")
    first = target_import.restore(request, bundle)
    replay = target_import.restore(request, bundle)
    no_change = target_import.restore(_request(key="portable-different-key"), bundle)

    assert replay.replayed is True
    assert replay.result_digest == first.result_digest
    assert no_change.result_state == "no_change"
    assert no_change.skipped[0].action == "skipped_identical"
    assert target_repo.current_version(record["record_id"]) == 1


def test_portable_restore_supports_version_plus_one_and_rejects_gaps(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    first = _create_memory(source_memories, key="portable-version")
    candidate = source_memories.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=first["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "updated"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    second = source_memories.commit_correction(candidate, idempotency_key="portable-version-v2")
    target_repo, target_memories, target_import = _services(tmp_path / "target")
    target_memories.commit_candidate(
        target_memories.propose_create(
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            memory_kind="shadow.memory.preference",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "original"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        ),
        idempotency_key="target-version-seed",
    )
    # Use the source stable record id for the target seed by importing version one first.
    target_import.restore(_request(key="portable-version-v1"), _bundle([first]))
    updated = target_import.restore(_request(key="portable-version-v2"), _bundle([second]))
    assert updated.imported[0].record_ref.version == 2
    assert target_repo.get(first["record_id"])["typed_payload"]["typed_content"] == {"text": "updated"}

    gap = deepcopy(second)
    gap["version"] = 4
    gap_bundle = _bundle([gap])
    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(_request(key="portable-version-gap"), gap_bundle)
    assert exc_info.value.error.code == "shadow.portable-import.version-conflict"


def test_portable_restore_conflict_is_all_or_nothing(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    first = _create_memory(source_memories, key="portable-atomic-a", text="a")
    second = _create_memory(source_memories, key="portable-atomic-b", text="b")
    target_repo, target_memories, target_import = _services(tmp_path / "target")
    target_import.restore(_request(key="portable-atomic-seed"), _bundle([first]))
    target_memories.commit_correction(
        target_memories.propose_correction(
            submitted_by="principal-test",
            owner_ref="principal-test",
            space_id="space-test",
            memory_id=first["record_id"],
            expected_version=1,
            memory_kind="shadow.memory.preference",
            content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
            typed_content={"text": "different"},
            applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        ),
        idempotency_key="portable-atomic-conflict",
    )
    conflicting_first = deepcopy(first)
    conflicting_first["typed_payload"]["typed_content"] = {"text": "conflicting import"}
    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(
            _request(key="portable-atomic-batch"), _bundle([conflicting_first, second])
        )
    assert exc_info.value.error.code == "shadow.portable-import.version-conflict"
    assert target_repo.get(second["record_id"]) is None


def test_portable_restore_tombstone_cannot_be_resurrected(tmp_path: Path) -> None:
    tombstone = json.loads(
        (ROOT / "contracts" / "fixtures" / "canonical" / "valid-tombstone-envelope.json").read_text()
    )
    tombstone["version"] = 1
    target_repo, _, target_import = _services(tmp_path / "target")
    result = target_import.restore(
        _request(
            principal_ref="principal-user-001",
            space_id="space-personal-001",
            key="portable-tombstone",
        ),
        _bundle([tombstone]),
    )
    assert result.imported[0].record_ref.version == 1
    active = deepcopy(tombstone)
    active["record_state"] = "active"
    active["version"] = 4
    active["typed_payload"] = {
        "memory_kind": "shadow.memory.preference",
        "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
        "typed_content": {"text": "resurrect"},
        "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        "evidence_refs": [],
        "source_refs": [],
        "source_dependency": "independent",
        "memory_state": "active",
        "supersedes_memory_refs": [],
        "created_from_ref": {"record_id": "old-candidate"},
    }
    with pytest.raises(ShadowDomainError) as exc_info:
        target_import.restore(
            _request(
                principal_ref="principal-user-001",
                space_id="space-personal-001",
                key="portable-tombstone-resurrect",
            ),
            _bundle([active]),
        )
    assert exc_info.value.error.code == "shadow.portable-import.version-conflict"
    assert target_repo.get(tombstone["record_id"])["record_state"] == "erased"


def test_portable_restore_store_unavailable_does_not_claim_success(tmp_path: Path) -> None:
    _, source_memories, _ = _services(tmp_path / "source")
    record = _create_memory(source_memories, key="portable-outage")
    target_repo, _, target_import = _services(tmp_path / "target")
    target_repo.set_available(False)
    with pytest.raises(RepositoryUnavailable):
        target_import.restore(_request(), _bundle([record]))
