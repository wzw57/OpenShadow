from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from shadow_adapters import DeterministicTestAdapter
from shadow_application import ConversationService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry
from shadow_store import (
    EXPORT_FORMAT,
    EXPORT_VERSION,
    SqliteCanonicalRepository,
    build_export_bundle,
    read_export_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def _repository_with_conversation(
    tmp_path: Path,
) -> tuple[SqliteCanonicalRepository, ContractRegistry]:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    service = ConversationService(
        repository, CommitAuthority(repository, registry), runtime_adapter=DeterministicTestAdapter()
    )
    conversation = service.create_conversation(
        owner_ref="principal-test", space_id="space-test", idempotency_key="export-conversation"
    )
    service.submit_turn(
        conversation_id=conversation["record_id"],
        principal_ref="principal-test",
        text="export me",
        idempotency_key="export-turn",
    )
    return repository, registry


def test_export_fixture_round_trips_canonical_records_and_digest(tmp_path: Path) -> None:
    repository, registry = _repository_with_conversation(tmp_path)

    bundle = repository.export_records(owner_refs={"principal-test"}, space_ids={"space-test"})
    assert bundle["format"] == EXPORT_FORMAT
    assert bundle["version"] == EXPORT_VERSION
    records = read_export_bundle(bundle)
    assert records == sorted(records, key=lambda record: (record["record_id"], record["version"]))
    assert len(records) >= 2
    for record in records:
        registry.validate_envelope(record)

    rebuilt = build_export_bundle(records, export_id="export-fixed")
    assert rebuilt["manifest_digest"] == bundle["manifest_digest"]
    assert read_export_bundle(rebuilt) == records


def test_export_fixture_rejects_manifest_record_and_duplicate_tampering(tmp_path: Path) -> None:
    repository, _ = _repository_with_conversation(tmp_path)
    bundle = repository.export_records(owner_refs={"principal-test"}, space_ids={"space-test"})

    manifest_tampered = deepcopy(bundle)
    manifest_tampered["records"][0]["owner_ref"] = "principal-tampered"
    with pytest.raises(ShadowDomainError) as manifest_error:
        read_export_bundle(manifest_tampered)
    assert manifest_error.value.error.code == "shadow.export.manifest-digest-mismatch"

    record_tampered = deepcopy(bundle)
    key = next(iter(record_tampered["record_digests"]))
    record_tampered["record_digests"][key] = sha256_digest({"tampered": True})
    record_tampered["manifest_digest"] = sha256_digest(
        {
            "format": record_tampered["format"],
            "version": record_tampered["version"],
            "records": record_tampered["records"],
            "record_digests": record_tampered["record_digests"],
        }
    )
    with pytest.raises(ShadowDomainError) as record_error:
        read_export_bundle(record_tampered)
    assert record_error.value.error.code == "shadow.export.record-digest-mismatch"

    with pytest.raises(ShadowDomainError) as duplicate_error:
        build_export_bundle([bundle["records"][0], bundle["records"][0]])
    assert duplicate_error.value.error.code == "shadow.export.duplicate-record"


def test_export_fixture_respects_repository_availability(tmp_path: Path) -> None:
    repository, _ = _repository_with_conversation(tmp_path)
    repository.set_available(False)
    with pytest.raises(RepositoryUnavailable):
        repository.export_records()
