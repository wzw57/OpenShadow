from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    text: str
    usage: dict[str, int]


class DeterministicTestAdapter:
    """A side-effect-free adapter used by Phase 0-1 tests and local smoke runs."""

    target_kind = "shadow.deterministic-runner"

    def execute(self, text: str) -> ExecutionResult:
        return ExecutionResult(
            text=f"Echo: {text}",
            usage={"input_characters": len(text), "output_characters": len(text) + 6},
        )
