from __future__ import annotations

from pathlib import Path

from shadow_adapters import DeterministicTestAdapter
from shadow_application import ConversationService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def test_restart_recovers_canonical_conversation_and_run_events(tmp_path: Path) -> None:
    database = tmp_path / "shadow.db"
    repository = SqliteCanonicalRepository(database)
    authority = CommitAuthority(repository, ContractRegistry(ROOT))
    service = ConversationService(
        repository, authority, runtime_adapter=DeterministicTestAdapter()
    )
    conversation = service.create_conversation(
        owner_ref="principal-test", space_id="space-test", idempotency_key="conversation-1"
    )
    result = service.submit_turn(
        conversation_id=conversation["record_id"],
        principal_ref="principal-test",
        text="recover me",
        idempotency_key="turn-1",
    )
    run_id = result.run["record_id"]
    assert DeterministicTestAdapter().events("deterministic:1") == []

    restarted = SqliteCanonicalRepository(database)
    recovered_conversation = restarted.get(conversation["record_id"])
    recovered_run = restarted.get(run_id)
    recovered_events = restarted.events(run_id)
    assert recovered_conversation is not None
    assert len(recovered_conversation["typed_payload"]["message_refs"]) == 2
    assert recovered_run and recovered_run["typed_payload"]["lifecycle"] == "completed"
    assert [event["event_type"] for event in recovered_events] == [
        "shadow.run.started",
        "shadow.run.completed",
    ]
