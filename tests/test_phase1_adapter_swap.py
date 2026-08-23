from __future__ import annotations

from pathlib import Path

from shadow_adapters import DeterministicTestAdapter, ExecutionResult
from shadow_application import ConversationService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.models import ExecutionRequest
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


class AlternateRuntimeAdapter(DeterministicTestAdapter):
    target_kind = "example.alternate.runner"

    def describe(self) -> dict[str, object]:
        body = super().describe()
        body.update(
            {
                "descriptor_id": "example.adapter.alternate",
                "implementation_ref": "example://alternate-runtime",
                "implementation_version": "1.0.0",
                "supported_target_kinds": [self.target_kind],
            }
        )
        return body

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        typed_input = request.typed_input
        text = typed_input.get("text", "") if isinstance(typed_input, dict) else str(typed_input)
        return ExecutionResult(
            text=f"Alternate: {text}",
            usage={"input_characters": len(text), "output_characters": len(text) + 10},
        )


def _service(runtime_adapter: DeterministicTestAdapter) -> ConversationService:
    repository = SqliteCanonicalRepository("sqlite://")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return ConversationService(repository, authority, runtime_adapter=runtime_adapter)


def test_replacing_runtime_keeps_shadow_ids_stable() -> None:
    default = _service(DeterministicTestAdapter())
    alternate = _service(AlternateRuntimeAdapter())
    default_conversation = default.create_conversation(
        owner_ref="principal-test", space_id="space-test", idempotency_key="conversation-swap"
    )
    alternate_conversation = alternate.create_conversation(
        owner_ref="principal-test", space_id="space-test", idempotency_key="conversation-swap"
    )
    default_turn = default.submit_turn(
        conversation_id=default_conversation["record_id"],
        principal_ref="principal-test",
        text="same identity",
        idempotency_key="turn-swap",
    )
    alternate_turn = alternate.submit_turn(
        conversation_id=alternate_conversation["record_id"],
        principal_ref="principal-test",
        text="same identity",
        idempotency_key="turn-swap",
    )

    assert alternate_conversation["record_id"] == default_conversation["record_id"]
    assert alternate_turn.run["record_id"] == default_turn.run["record_id"]
    assert alternate_turn.user_message["record_id"] == default_turn.user_message["record_id"]
    assert alternate_turn.assistant_message["record_id"] == default_turn.assistant_message["record_id"]
    assert alternate_turn.run["typed_payload"]["request_ref"] == default_turn.run["typed_payload"]["request_ref"]
    assert alternate_turn.assistant_message["typed_payload"]["content_blocks"][0]["typed_content"] == {
        "text": "Alternate: same identity"
    }
    assert alternate_turn.run["typed_payload"]["binding_refs"]
    binding = alternate.repository.get(
        alternate_turn.run["typed_payload"]["binding_refs"][0]["record_id"]
    )
    assert binding["typed_payload"]["target_kind"] == "example.alternate.runner"
