from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DeterministicCrossComponentErasureAdapter:
    """Records quiesce/erase order and never mutates Canonical state."""

    calls: list[tuple[str, str]] = field(default_factory=list)

    def quiesce(self, request: dict[str, Any], component_ref: str) -> list[str]:
        self.calls.append(("quiesce", component_ref))
        del request
        return [f"evidence:{component_ref}:quiesced"]

    def erase(self, request: dict[str, Any], component_ref: str) -> list[str]:
        self.calls.append(("erase", component_ref))
        del request
        return [f"evidence:{component_ref}:erased"]
