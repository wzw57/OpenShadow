from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shadow_adapters import ExecutionResult
from shadow_application import ConversationService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.ids import sha256_digest
from shadow_kernel.models import ExecutionRequest
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class InspectingAdapter:
    repository: SqliteCanonicalRepository
    fail: bool = False
    calls: int = 0

    target_kind = "shadow.test-reliability"

    def describe(self) -> dict[str, object]:
        return {
            "descriptor_id": "shadow.adapter.reliability-test",
            "descriptor_version": "1.0.0",
            "adapter_family": "shadow.execution",
            "implementation_ref": "openshadow://tests/reliability",
            "implementation_version": "1.0.0",
            "supported_contracts": [{"contract_id": "shadow.execution", "version_range": "1.0.0"}],
            "supported_target_kinds": [self.target_kind],
            "capabilities": [],
            "config_schema_ref": "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor",
        }

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls += 1
        if self.fail:
            raise TimeoutError("provider did not confirm the outcome")
        typed_input = request.typed_input
        text = typed_input.get("text", "") if isinstance(typed_input, dict) else str(typed_input)
        return ExecutionResult(text=f"processed: {text}", usage={"calls": self.calls})

    def events(self, execution_ref: str, after_cursor: str | None = None) -> list[dict[str, object]]:
        return []


def _service(adapter: InspectingAdapter) -> tuple[ConversationService, dict[str, object]]:
    authority = CommitAuthority(adapter.repository, ContractRegistry(ROOT))
    service = ConversationService(adapter.repository, authority, runtime_adapter=adapter)
    conversation = service.create_conversation(owner_ref="principal-reliability", space_id="space-test", idempotency_key="conv")
    return service, conversation


def test_attempt_is_durable_before_provider_and_replay_does_not_call_again() -> None:
    repository = SqliteCanonicalRepository("sqlite://")
    adapter = InspectingAdapter(repository)
    service, conversation = _service(adapter)
    result = service.submit_turn(
        conversation_id=str(conversation["record_id"]), principal_ref="principal-reliability", text="hello", idempotency_key="turn-reliability"
    )
    assert adapter.calls == 1
    token = sha256_digest({"conversation": conversation["record_id"], "key": "turn-reliability"})[7:31]
    assert repository.get(f"attempt-{token}")["typed_payload"]["lifecycle"] == "succeeded"
    replay = service.submit_turn(
        conversation_id=str(conversation["record_id"]), principal_ref="principal-reliability", text="hello", idempotency_key="turn-reliability"
    )
    assert replay.replayed is True
    assert adapter.calls == 1
    assert result.run["typed_payload"]["lifecycle"] == "completed"


def test_provider_timeout_is_persisted_as_unknown_without_assistant_message() -> None:
    repository = SqliteCanonicalRepository("sqlite://")
    adapter = InspectingAdapter(repository, fail=True)
    service, conversation = _service(adapter)
    result = service.submit_turn(
        conversation_id=str(conversation["record_id"]), principal_ref="principal-reliability", text="uncertain", idempotency_key="turn-unknown"
    )
    assert result.assistant_message == {}
    assert result.run["typed_payload"]["lifecycle"] == "waiting"
    assert repository.events(result.run["record_id"])[-1]["event_type"] == "shadow.run.unknown"
