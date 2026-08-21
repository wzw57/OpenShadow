from __future__ import annotations

from pathlib import Path

from shadow_kernel.commit import CommitAuthority
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    ConversationPayload,
    Provenance,
    StableRecordRef,
)
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA = "https://schemas.openshadow.dev/contracts/profiles/1.0.0"


def _operation(
    record_id: str, operation: str = "create", expected_version: int | None = None
) -> CommitOperation:
    payload = ConversationPayload(conversation_state="open", message_refs=[], queued_run_refs=[])
    return CommitOperation(
        operation_id=f"operation-{record_id}-{operation}",
        operation=operation,
        record_id=record_id,
        record_type="shadow.profile.conversation",
        target_schema_ref=f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
        owner_ref="principal-test",
        space_id="space-test",
        created_by="principal-test",
        data_classification="personal",
        provenance=Provenance(origin_type="shadow.origin.test", origin_ref="test"),
        retention_policy_ref=StableRecordRef(record_id="retention-default"),
        typed_payload=payload.model_dump(mode="json", exclude_none=True),
        expected_version=expected_version,
    )


def _plan(operation: CommitOperation, key: str) -> CommitPlan:
    return CommitPlan(
        commit_request_id=f"commit-request-{key}",
        idempotency_scope="test",
        idempotency_key=key,
        request_digest=sha256_digest(operation.model_dump(mode="json")),
        actor_ref="principal-test",
        operations=[operation],
        prepared_at=utc_timestamp(),
    )


def test_atomic_create_and_expected_version_conflict(tmp_path: Path) -> None:
    registry = ContractRegistry(ROOT)
    repository = CanonicalRepository(tmp_path / "shadow.db")
    authority = CommitAuthority(repository, registry)
    first = authority.commit(_plan(_operation("conversation-1"), "create-1"))
    assert first.outcome == "committed"
    assert first.operation_results[0].resulting_version == 1

    conflict = authority.commit(
        _plan(_operation("conversation-1", "update", expected_version=99), "conflict-1")
    )
    assert conflict.outcome == "conflict"
    assert conflict.commit_id is None
    assert conflict.operation_results[0].conflict_current_version == 1
    assert repository.get("conversation-1")["version"] == 1


def test_committed_batch_replays_exactly(tmp_path: Path) -> None:
    registry = ContractRegistry(ROOT)
    repository = CanonicalRepository(tmp_path / "shadow.db")
    authority = CommitAuthority(repository, registry)
    plan = _plan(_operation("conversation-2"), "replay-1")
    first = authority.commit(plan)
    replay = authority.commit(plan)
    assert first.outcome == "committed"
    assert replay.outcome == "idempotent_replay"
    assert replay.commit_id == first.commit_id
    assert repository.get("conversation-2")["version"] == 1
