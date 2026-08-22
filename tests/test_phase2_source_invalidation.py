from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from shadow_adapters import (
    DeterministicMemoryIndexAdapter,
    DeterministicMemoryRecallAdapter,
)
from shadow_application import (
    MemoryIndexRebuildService,
    MemoryRecallService,
    MemoryService,
    MemorySourceInvalidationRequest,
    MemorySourceInvalidationResult,
    MemorySourceInvalidationService,
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
    source_dependency: str = "dependent",
    source_refs: list[str] | None = None,
    owner_ref: str = "principal-test",
    space_id: str = "space-test",
    text: str = "source-backed preference",
) -> dict:
    candidate = service.propose_create(
        submitted_by=owner_ref,
        owner_ref=owner_ref,
        space_id=space_id,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": text},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
        source_refs=source_refs or ["integration:calendar/account-1"],
        source_dependency=source_dependency,
    )
    return service.commit_candidate(candidate, idempotency_key=key)


def _request(
    record: dict,
    *,
    request_id: str = "source-request-1",
    idempotency_key: str = "source-event-1",
    source_ref: str = "integration:calendar/account-1",
    source_state: str = "deleted",
    principal_ref: str = "principal-test",
    space_id: str = "space-test",
    version: int | None = None,
) -> MemorySourceInvalidationRequest:
    return MemorySourceInvalidationRequest(
        principal_ref=principal_ref,
        space_id=space_id,
        source_ref=source_ref,
        source_event_ref=f"calendar-event-{request_id}",
        source_state=source_state,
        targets=[{"record_id": record["record_id"], "version": version or record["version"]}],
        idempotency_key=idempotency_key,
        request_id=request_id,
        observed_at="2026-08-22T00:00:00Z",
        reason="Source state changed",
    )


def test_dependent_invalidation_creates_invalidated_version(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-dependent")
    result = MemorySourceInvalidationService(memories).invalidate(_request(original))
    current = repository.get(original["record_id"])

    assert result.result_state == "committed"
    assert result.targets[0].action == "invalidated"
    assert result.targets[0].previous_version == 1
    assert result.targets[0].resulting_version == 2
    assert current["record_state"] == "active"
    assert current["typed_payload"]["memory_state"] == "invalidated"
    assert current["provenance"]["origin_type"] == "shadow.origin.source-event"
    assert repository.current_version(original["record_id"]) == 2


def test_independent_and_review_required_do_not_mutate_canonical(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    independent = _create_memory(
        memories,
        key="source-independent",
        source_dependency="independent",
    )
    review = _create_memory(
        memories,
        key="source-review",
        source_dependency="review_required",
    )
    service = MemorySourceInvalidationService(memories)

    retained = service.invalidate(_request(independent, request_id="independent"))
    reviewed = service.invalidate(_request(review, request_id="review"))

    assert retained.result_state == "no_change"
    assert retained.targets[0].action == "retained"
    assert reviewed.result_state == "review_required"
    assert reviewed.targets[0].action == "review_required"
    assert repository.current_version(independent["record_id"]) == 1
    assert repository.current_version(review["record_id"]) == 1


def test_mixed_batch_is_all_or_nothing_on_source_binding_error(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    dependent = _create_memory(memories, key="source-batch-dependent")
    unrelated = _create_memory(
        memories,
        key="source-batch-unrelated",
        source_refs=["integration:mail/account-1"],
    )
    request = MemorySourceInvalidationRequest(
        principal_ref="principal-test",
        space_id="space-test",
        source_ref="integration:calendar/account-1",
        source_event_ref="calendar-event-batch",
        source_state="deleted",
        targets=[
            {"record_id": dependent["record_id"], "version": 1},
            {"record_id": unrelated["record_id"], "version": 1},
        ],
        idempotency_key="source-batch",
        request_id="source-batch",
        observed_at="2026-08-22T00:00:00Z",
        reason="Batch source deletion",
    )

    with pytest.raises(ShadowDomainError) as invalid:
        MemorySourceInvalidationService(memories).invalidate(request)

    assert invalid.value.error.code == "shadow.memory.source-not-attached"
    assert repository.current_version(dependent["record_id"]) == 1
    assert repository.current_version(unrelated["record_id"]) == 1


def test_owner_space_and_store_errors_are_structured(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-owner")
    with pytest.raises(ShadowDomainError) as unauthorized:
        MemorySourceInvalidationService(memories).invalidate(
            _request(original, request_id="wrong-owner", principal_ref="principal-other")
        )
    assert unauthorized.value.error.code == "shadow.memory.source-owner-space-mismatch"

    repository.set_available(False)
    with pytest.raises(ShadowDomainError) as unavailable:
        MemorySourceInvalidationService(memories).invalidate(
            _request(original, request_id="store-down")
        )
    assert unavailable.value.error.code == "shadow.memory.source-invalidation-unavailable"


def test_source_event_replay_does_not_create_new_version(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-replay")
    service = MemorySourceInvalidationService(memories)
    request = _request(original, request_id="replay", idempotency_key="source-replay-event")
    first = service.invalidate(request)
    replay = service.invalidate(request)

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.result_digest == first.result_digest
    assert repository.current_version(original["record_id"]) == 2


def test_source_event_replay_conflict_is_rejected(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-replay-conflict")
    service = MemorySourceInvalidationService(memories)
    service.invalidate(_request(original, request_id="replay-conflict"))

    with pytest.raises(ShadowDomainError) as conflict:
        service.invalidate(
            _request(
                original,
                request_id="replay-conflict-different",
                idempotency_key="source-event-1",
            )
        )

    assert conflict.value.error.code == "shadow.memory.source-replay-conflict"
    assert repository.current_version(original["record_id"]) == 2


def test_source_event_with_new_idempotency_key_hits_head_conflict(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-head-conflict")
    service = MemorySourceInvalidationService(memories)
    service.invalidate(_request(original, request_id="head-conflict-first"))

    with pytest.raises(ShadowDomainError) as conflict:
        service.invalidate(
            _request(
                original,
                request_id="head-conflict-second",
                idempotency_key="source-event-new-key",
            )
        )

    assert conflict.value.error.code == "shadow.memory.source-head-conflict"
    assert repository.current_version(original["record_id"]) == 2


def test_restored_source_never_reactivates_invalidated_memory(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-restored")
    service = MemorySourceInvalidationService(memories)
    service.invalidate(_request(original, request_id="delete-before-restore"))
    invalidated = repository.get(original["record_id"])
    restored = service.invalidate(
        _request(
            original,
            request_id="restore",
            idempotency_key="source-restore",
            source_state="restored",
            version=invalidated["version"],
        )
    )

    assert restored.result_state == "unsupported"
    assert restored.targets[0].action == "unsupported"
    assert repository.current_version(original["record_id"]) == 2
    assert repository.get(original["record_id"])["typed_payload"]["memory_state"] == "invalidated"


def test_invalidated_memory_is_excluded_from_list_recall_and_index(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-anti-resurrection")
    MemorySourceInvalidationService(memories).invalidate(_request(original))

    assert memories.list_memories(owner_ref="principal-test", space_id="space-test") == []
    recall = MemoryRecallService(repository, DeterministicMemoryRecallAdapter()).recall(
        {
            "principal_ref": "principal-test",
            "space_id": "space-test",
            "query_text": "source",
            "request_id": "recall-invalidated",
        }
    )
    index = MemoryIndexRebuildService(repository, DeterministicMemoryIndexAdapter()).rebuild(
        {
            "principal_ref": "principal-test",
            "space_id": "space-test",
            "rebuild_request_id": "index-invalidated",
            "index_revision": "deterministic-v1",
            "index_schema_ref": "https://schemas.openshadow.dev/index/memory/1.0.0",
        }
    )

    assert recall.items == []
    assert index.entries == []


def test_old_candidate_cannot_reactivate_invalidated_head(tmp_path: Path) -> None:
    repository, memories, _ = _services(tmp_path)
    original = _create_memory(memories, key="source-candidate")
    candidate = memories.propose_correction(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_id=original["record_id"],
        expected_version=1,
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "old candidate"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    MemorySourceInvalidationService(memories).invalidate(_request(original))

    with pytest.raises(ShadowDomainError) as rejected:
        memories.commit_correction(candidate, idempotency_key="old-candidate-after-source")

    assert rejected.value.error.code == "shadow.repository.expected-version-conflict"
    assert repository.current_version(original["record_id"]) == 2


def test_source_invalidation_restart_preserves_invalidated_version(tmp_path: Path) -> None:
    database = tmp_path / "restart.db"
    repository = SqliteCanonicalRepository(database)
    registry = ContractRegistry(ROOT)
    memories = MemoryService(repository, CommitAuthority(repository, registry), registry)
    original = _create_memory(memories, key="source-restart")
    MemorySourceInvalidationService(memories).invalidate(_request(original))

    restarted = SqliteCanonicalRepository(database)
    recovered = restarted.get(original["record_id"])

    assert recovered["version"] == 2
    assert recovered["record_state"] == "active"
    assert recovered["typed_payload"]["memory_state"] == "invalidated"


@pytest.mark.parametrize(
    ("relative_path", "model"),
    [
        (
            "source-invalidation/valid-memory-source-invalidation-request.json",
            MemorySourceInvalidationRequest,
        ),
        (
            "source-invalidation/valid-memory-source-invalidation-result.json",
            MemorySourceInvalidationResult,
        ),
    ],
)
def test_valid_source_invalidation_contract_fixtures(relative_path: str, model: type) -> None:
    payload = json.loads((ROOT / "contracts" / "fixtures" / relative_path).read_text())
    model.model_validate(payload)


def test_invalid_source_invalidation_contract_fixtures_are_rejected() -> None:
    invalid_request = json.loads(
        (
            ROOT
            / "contracts"
            / "fixtures"
            / "source-invalidation/invalid-memory-source-invalidation-request.json"
        ).read_text()
    )
    invalid_result = json.loads(
        (
            ROOT
            / "contracts"
            / "fixtures"
            / "source-invalidation/invalid-memory-source-invalidation-result.json"
        ).read_text()
    )
    with pytest.raises((ValueError, ValidationError)):
        MemorySourceInvalidationRequest.model_validate(invalid_request)
    with pytest.raises((ValueError, ValidationError)):
        MemorySourceInvalidationResult.model_validate(invalid_result)
