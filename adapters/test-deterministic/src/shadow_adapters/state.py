from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DeterministicStateSourceAdapter:
    """Contract fixture that returns an Observation and never commits it."""

    source_ref: str = "adapter:deterministic-state"
    value: Any = True
    available: bool = True
    observed_at: str = "2026-08-22T08:00:00Z"
    expires_at: str = "2026-08-22T09:00:00Z"

    def observe(self, *, state_key: str, owner_ref: str, space_id: str) -> dict[str, Any]:
        del owner_ref, space_id
        availability = "available" if self.available else "unavailable"
        return {
            "state_key": state_key,
            "value_schema_ref": "https://schemas.openshadow.dev/examples/deterministic-state/1.0.0",
            "observed_value": self.value,
            "evidence_refs": [
                {
                    "evidence_id": f"evidence-{state_key}",
                    "source_ref": self.source_ref,
                    "availability": availability,
                    "observed_at": self.observed_at,
                }
            ],
            "source_refs": [self.source_ref],
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "source_status": availability,
        }
