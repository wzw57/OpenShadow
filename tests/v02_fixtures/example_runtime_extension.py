"""A dependency-free typed Runtime Extension fixture for the R0 gate."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExampleExecutionRequest:
    request_id: str
    target_kind: str
    typed_input: dict[str, Any]
    capability_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExampleExecutionResult:
    request_id: str
    outcome: str
    output: dict[str, Any]


class ExampleRuntimeExtension:
    """Minimal typed runtime shape; no vendor or application dependency."""

    extension_id = "example.runtime"
    version = "0.1.0"
    target_kind = "example.runtime.v1"
    capabilities = frozenset({"example.execute"})

    def describe(self) -> dict[str, Any]:
        return {
            "extension_id": self.extension_id,
            "version": self.version,
            "target_kind": self.target_kind,
            "capabilities": sorted(self.capabilities),
        }

    def execute(self, request: ExampleExecutionRequest) -> ExampleExecutionResult:
        if request.target_kind != self.target_kind:
            raise ValueError("Unsupported example runtime target")
        return ExampleExecutionResult(
            request_id=request.request_id,
            outcome="succeeded",
            output={"echo": request.typed_input},
        )

    def events(
        self, execution_ref: str, after_cursor: str | None = None
    ) -> Iterable[dict[str, Any]]:
        del after_cursor
        return ({"execution_ref": execution_ref, "event_type": "completed"},)


__all__ = ["ExampleExecutionRequest", "ExampleExecutionResult", "ExampleRuntimeExtension"]
