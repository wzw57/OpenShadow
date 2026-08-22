from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeterministicOutboxAdapter:
    """Contract adapter: returns configured outcomes and never commits records."""

    outcome: str = "delivered"
    provider_ref: str = "deterministic-outbox-provider"
    reconcile_outcome: str | None = None
    deliver_calls: int = 0
    reconcile_calls: int = 0

    def deliver(self, intent: dict[str, Any]) -> dict[str, Any]:
        self.deliver_calls += 1
        result: dict[str, Any] = {
            "outcome": self.outcome,
            "provider_ref": self.provider_ref,
            "observed_at": "2026-08-22T08:01:00Z",
        }
        if self.outcome in {"failed", "unknown"}:
            result["reason"] = (
                "deterministic provider failed"
                if self.outcome == "failed"
                else "deterministic provider outcome uncertain"
            )
        del intent
        return result

    def reconcile(self, intent: dict[str, Any]) -> dict[str, Any]:
        self.reconcile_calls += 1
        outcome = self.reconcile_outcome or "unknown"
        result: dict[str, Any] = {
            "outcome": outcome,
            "provider_ref": intent.get("typed_payload", {}).get("provider_ref", self.provider_ref),
            "evidence_refs": ["deterministic-outbox-evidence"],
            "observed_at": "2026-08-22T08:05:00Z",
        }
        del intent
        return result
