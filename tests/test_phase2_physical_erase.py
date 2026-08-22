from __future__ import annotations

from pathlib import Path

import pytest
from shadow_adapters import DeterministicErasureAdapter
from shadow_application import MemoryService, PhysicalEraseRequest, PhysicalEraseService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError
from shadow_kernel.models import StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def _services(
    tmp_path: Path,
    adapter: DeterministicErasureAdapter | None = None,
) -> tuple[SqliteCanonicalRepository, MemoryService, PhysicalEraseService, DeterministicErasureAdapter]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    memories = MemoryService(repository, authority, registry)
    adapter = adapter or DeterministicErasureAdapter()
    return repository, memories, PhysicalEraseService(repository, authority, adapter), adapter


def _create_memory(service: MemoryService, *, key: str, text: str = "erase me") -> dict:
    candidate = service.propose_create(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": text},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    return service.commit_candidate(candidate, idempotency_key=key)


def _request(record: dict, *, key: str = "erase-1", version: int | None = None) -> PhysicalEraseRequest:
    return PhysicalEraseRequest(
        principal_ref="principal-test",
        space_id="space-test",
        record_id=record["record_id"],
        expected_version=version or record["version"],
        erasure_ref=StableRecordRef(record_id="erasure-request-1"),
        relation_refs=[StableRecordRef(record_id="relation-a")],
        request_id="erase-request-1",
        idempotency_key=key,
    )


def test_physical_erase_order_tombstone_and_history_purge(tmp_path: Path) -> None:
    repository, memories, service, adapter = _services(tmp_path)
    record = _create_memory(memories, key="erase-create")
    result = service.erase(_request(record))

    assert result.result_state == "committed"
    assert result.record_ref.version == 2
    assert adapter.calls == ["quiesce", "erase", "finalize"]
    assert repository.get(record["record_id"], 1) is None
    tombstone = repository.get(record["record_id"])
    assert tombstone["record_state"] == "erased"
    assert tombstone["typed_payload"] == {
        "erased": True,
        "erasure_ref": {"record_id": "erasure-request-1"},
        "non_sensitive_relation_refs": [{"record_id": "relation-a"}],
    }
    assert "typed_content" not in tombstone["typed_payload"]
    assert repository.query(record_states={"active", "logically_deleted"}) == []


def test_logically_deleted_record_can_be_physically_erased(tmp_path: Path) -> None:
    repository, memories, service, _ = _services(tmp_path)
    record = _create_memory(memories, key="erase-logical")
    deleted = memories.logical_delete(
        memory_id=record["record_id"],
        expected_version=1,
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        idempotency_key="erase-logical-delete",
    )
    result = service.erase(_request(deleted, key="erase-after-logical"))
    assert result.record_ref.version == 3
    assert repository.get(record["record_id"], 1) is None
    assert repository.get(record["record_id"], 2) is None
    assert repository.get(record["record_id"])["record_state"] == "erased"


def test_erase_replay_is_stable_and_does_not_repeat_external_erase(tmp_path: Path) -> None:
    repository, memories, service, adapter = _services(tmp_path)
    record = _create_memory(memories, key="erase-replay-create")
    request = _request(record, key="erase-replay")
    first = service.erase(request)
    replay = service.erase(request)

    assert replay.result_state == "replayed"
    assert replay.replayed is True
    assert replay.record_ref == first.record_ref
    assert replay.result_digest == first.result_digest
    assert adapter.calls == ["quiesce", "erase", "finalize", "finalize"]
    assert repository.current_version(record["record_id"]) == 2


def test_erase_replay_conflict_and_owner_version_errors(tmp_path: Path) -> None:
    _, memories, service, _ = _services(tmp_path)
    record = _create_memory(memories, key="erase-errors")
    request = _request(record, key="erase-error-key")
    service.erase(request)
    with pytest.raises(ShadowDomainError) as replay_exc:
        service.erase(request.model_copy(update={"erasure_ref": StableRecordRef(record_id="other")}))
    assert replay_exc.value.error.code == "shadow.erasure.replay-conflict"

    with pytest.raises(ShadowDomainError) as owner_exc:
        service.erase(
            request.model_copy(
                update={"principal_ref": "principal-other", "idempotency_key": "erase-owner-mismatch"}
            )
        )
    assert owner_exc.value.error.code == "shadow.erasure.owner-space-mismatch"

    other = _create_memory(memories, key="erase-other")
    with pytest.raises(ShadowDomainError) as owner_exc:
        service.erase(_request(other, key="erase-unrelated", version=99))
    assert owner_exc.value.error.code == "shadow.erasure.version-conflict"



def test_erase_already_erased_and_old_candidate_cannot_resurrect(tmp_path: Path) -> None:
    repository, memories, service, _ = _services(tmp_path)
    record = _create_memory(memories, key="erase-anti-resurrection")
    service.erase(_request(record))
    with pytest.raises(ShadowDomainError) as exc_info:
        service.erase(_request(record, key="erase-again", version=2))
    assert exc_info.value.error.code == "shadow.erasure.already-erased"
    with pytest.raises(ShadowDomainError) as candidate_exc:
        memories.commit_correction(
            memories.propose_correction(
                submitted_by="principal-test",
                owner_ref="principal-test",
                space_id="space-test",
                memory_id=record["record_id"],
                expected_version=1,
                memory_kind="shadow.memory.preference",
                content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                typed_content={"text": "resurrect"},
                applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
            ),
            idempotency_key="erase-old-candidate",
        )
    assert candidate_exc.value.error.code in {"shadow.memory.not-found", "shadow.memory.head-not-active"}
    assert repository.get(record["record_id"])["record_state"] == "erased"


def test_adapter_unavailable_prevents_canonical_commit(tmp_path: Path) -> None:
    adapter = DeterministicErasureAdapter(state="unavailable")
    repository, memories, service, _ = _services(tmp_path, adapter)
    record = _create_memory(memories, key="erase-adapter-outage")
    with pytest.raises(ShadowDomainError) as exc_info:
        service.erase(_request(record))
    assert exc_info.value.error.code == "shadow.erasure.adapter-unavailable"
    assert repository.current_version(record["record_id"]) == 1


def test_finalize_failure_is_not_reported_as_success_and_replay_can_retry(tmp_path: Path) -> None:
    adapter = DeterministicErasureAdapter(finalize_state="unavailable")
    repository, memories, service, _ = _services(tmp_path, adapter)
    record = _create_memory(memories, key="erase-finalize-create")
    request = _request(record, key="erase-finalize")
    with pytest.raises(ShadowDomainError) as exc_info:
        service.erase(request)
    assert exc_info.value.error.code == "shadow.erasure.finalize-failed"
    assert repository.get(record["record_id"])["record_state"] == "erased"
    assert repository.get(record["record_id"], 1) is None

    adapter.finalize_state = "ready"
    replay = service.erase(request)
    assert replay.result_state == "replayed"
    assert replay.replayed is True


def test_store_unavailable_does_not_claim_erase_success(tmp_path: Path) -> None:
    repository, memories, service, _ = _services(tmp_path)
    record = _create_memory(memories, key="erase-store-outage")
    repository.set_available(False)
    with pytest.raises(RepositoryUnavailable):
        service.erase(_request(record))
