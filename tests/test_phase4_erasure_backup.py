from __future__ import annotations

from pathlib import Path

import pytest
from shadow_adapters import DeterministicCrossComponentErasureAdapter
from shadow_application import BackupMetadataService, ErasureService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(tmp_path: Path) -> tuple[SqliteCanonicalRepository, ErasureService, BackupMetadataService]:
    repository = SqliteCanonicalRepository(f"sqlite:///{(tmp_path / 'erasure.db').as_posix()}")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, ErasureService(repository, authority, registry), BackupMetadataService(repository, authority, registry)


def _candidate(service: ErasureService):
    return service.propose_request(
        owner_ref="principal-erasure",
        space_id="space-erasure",
        scope_ref="memory:memory-1",
        target_refs=["memory-1", "index-entry-1", "backup-copy-1"],
        policy_ref={"record_id": "policy-default", "version": 1},
        idempotency_key="erase-key-1",
        component_statuses=[
            {"component_ref": "memory-store", "capability_family": "canonical", "state": "pending", "updated_at": "2026-08-22T08:00:00Z", "evidence_refs": []},
            {"component_ref": "backup-1", "capability_family": "backup", "state": "pending", "updated_at": "2026-08-22T08:00:00Z", "evidence_refs": []},
        ],
    )


def _metadata() -> dict[str, object]:
    return {
        "backup_id": "backup-metadata-1",
        "format_version": "1.0.0",
        "owner_ref": "principal-erasure",
        "space_id": "space-erasure",
        "export_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "manifest_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "encrypted": True,
        "key_ref": "vault-key-ref-opaque",
        "created_at": "2026-08-22T08:00:00Z",
        "retention_until": "2099-01-01T00:00:00Z",
        "excluded_content_classes": ["secret", "provider-private-state", "derived-index", "cache"],
        "erase_schedule_ref": "erasure-request-1",
    }


def test_erasure_dispatch_persists_quiesce_before_erase_and_unknown_is_not_complete(tmp_path: Path) -> None:
    repository, service, _ = _services(tmp_path)
    created = service.create_request(_candidate(service))
    request_id = created["record"]["record_id"]
    adapter = DeterministicCrossComponentErasureAdapter()
    partial = service.dispatch_component(
        request_id=request_id, expected_version=1, owner_ref="principal-erasure", space_id="space-erasure",
        component_ref="memory-store", adapter=adapter, idempotency_key="dispatch-memory",
    )
    assert adapter.calls == [("quiesce", "memory-store"), ("erase", "memory-store")]
    assert partial["record"]["typed_payload"]["lifecycle"] in {"pending", "partially_completed", "dispatching"}
    assert partial["record"]["typed_payload"]["component_statuses"][0]["state"] == "erased"
    unknown = service.update_component_status(
        request_id=request_id, expected_version=3, owner_ref="principal-erasure", space_id="space-erasure",
        component_ref="backup-1", state="unreachable", evidence_refs=[], idempotency_key="backup-unreachable",
    )
    assert unknown["record"]["typed_payload"]["lifecycle"] == "partially_completed"
    assert repository.current_version(request_id) == 4


def test_all_components_erased_reaches_completed_and_replay_is_stable(tmp_path: Path) -> None:
    _, service, _ = _services(tmp_path)
    created = service.create_request(_candidate(service))
    request_id = created["record"]["record_id"]
    first = service.update_component_status(
        request_id=request_id, expected_version=1, owner_ref="principal-erasure", space_id="space-erasure",
        component_ref="memory-store", state="erased", evidence_refs=["memory-erased"], idempotency_key="memory-erased",
    )
    completed = service.update_component_status(
        request_id=request_id, expected_version=2, owner_ref="principal-erasure", space_id="space-erasure",
        component_ref="backup-1", state="erased", evidence_refs=["backup-erased"], idempotency_key="backup-erased",
    )
    replay = service.update_component_status(
        request_id=request_id, expected_version=2, owner_ref="principal-erasure", space_id="space-erasure",
        component_ref="backup-1", state="erased", evidence_refs=["backup-erased"], idempotency_key="backup-erased",
    )
    assert first["record"]["version"] == 2
    assert completed["record"]["typed_payload"]["lifecycle"] == "completed"
    assert replay["replayed"] is True
    with pytest.raises(ShadowDomainError) as error:
        service.update_component_status(
            request_id=request_id, expected_version=3, owner_ref="principal-erasure", space_id="space-erasure",
            component_ref="backup-1", state="pending", evidence_refs=[], idempotency_key="resurrect",
        )
    assert error.value.error.code == "shadow.erasure.already-completed"


def test_backup_metadata_is_encrypted_metadata_only_and_replay_safe(tmp_path: Path) -> None:
    repository, _, backups = _services(tmp_path)
    registered = backups.register(owner_ref="principal-erasure", space_id="space-erasure", metadata=_metadata(), idempotency_key="backup-key")
    replay = backups.register(owner_ref="principal-erasure", space_id="space-erasure", metadata=_metadata(), idempotency_key="backup-key")
    assert registered["record"]["record_type"] == "shadow.backup.metadata"
    assert replay["replayed"] is True
    assert repository.current_version("backup-metadata-backup-metadata-1") == 1
    invalid = _metadata()
    invalid["encrypted"] = False
    with pytest.raises(ShadowDomainError) as error:
        backups.register(owner_ref="principal-erasure", space_id="space-erasure", metadata=invalid, idempotency_key="backup-invalid")
    assert error.value.error.code == "shadow.backup.encryption-required"


def test_owner_mismatch_and_store_outage_do_not_claim_erasure(tmp_path: Path) -> None:
    repository, service, _ = _services(tmp_path)
    created = service.create_request(_candidate(service))
    request_id = created["record"]["record_id"]
    with pytest.raises(ShadowDomainError) as unauthorized:
        service.update_component_status(
            request_id=request_id, expected_version=1, owner_ref="other", space_id="space-erasure",
            component_ref="memory-store", state="erased", evidence_refs=[], idempotency_key="other",
        )
    assert unauthorized.value.error.code == "shadow.erasure.unauthorized"
    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as unavailable:
        service.update_component_status(
            request_id=request_id, expected_version=1, owner_ref="principal-erasure", space_id="space-erasure",
            component_ref="memory-store", state="erased", evidence_refs=[], idempotency_key="outage",
        )
    assert unavailable.value.error.code == "shadow.repository.unavailable"
