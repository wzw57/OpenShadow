from __future__ import annotations

from dataclasses import dataclass

from shadow_kernel.models import ExecutionRequest


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    text: str
    usage: dict[str, int]


class DeterministicTestAdapter:
    """A side-effect-free adapter used by Phase 0-1 tests and local smoke runs."""

    target_kind = "shadow.deterministic-runner"

    def describe(self) -> dict[str, object]:
        return {
            "descriptor_id": "shadow.adapter.deterministic",
            "descriptor_version": "1.0.0",
            "adapter_family": "shadow.execution",
            "implementation_ref": "openshadow://adapters/test-deterministic",
            "implementation_version": "0.1.0",
            "supported_contracts": [
                {"contract_id": "shadow.execution", "version_range": "1.0.0"}
            ],
            "supported_target_kinds": [self.target_kind],
            "capabilities": [],
            "config_schema_ref": (
                "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor"
            ),
        }

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        typed_input = request.typed_input
        text = typed_input.get("text", "") if isinstance(typed_input, dict) else str(typed_input)
        return ExecutionResult(
            text=f"Echo: {text}",
            usage={"input_characters": len(text), "output_characters": len(text) + 6},
        )

    def events(self, execution_ref: str, after_cursor: str | None = None) -> list[dict[str, object]]:
        return []
