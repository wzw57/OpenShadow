from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeterministicActionProvider:
    """Contract adapter: returns configured outcomes and never commits records."""

    outcome: str = "succeeded"
    external_ref: str = "deterministic-provider-operation"
    reconcile_outcome: str | None = None
    execute_calls: int = 0
    reconcile_calls: int = 0

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        self.execute_calls += 1
        result: dict[str, Any] = {
            "outcome": self.outcome,
            "external_ref": self.external_ref,
            "observed_at": "2026-08-22T08:00:00Z",
        }
        if self.outcome == "failed":
            result["failure_summary"] = {"code": "deterministic.provider-failed"}
        if self.outcome == "unknown":
            result["unknown_reason"] = "deterministic transport uncertainty"
        del action
        return result

    def reconcile(self, action: dict[str, Any]) -> dict[str, Any]:
        self.reconcile_calls += 1
        outcome = self.reconcile_outcome or "unknown"
        result: dict[str, Any] = {
            "outcome": outcome,
            "external_ref": action.get("typed_payload", {}).get("external_ref", self.external_ref),
            "observed_at": "2026-08-22T08:05:00Z",
            "evidence_refs": [{"record_id": "deterministic-provider-evidence"}],
            "reason": "deterministic reconciliation result",
        }
        del action
        return result
