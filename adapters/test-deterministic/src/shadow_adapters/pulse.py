from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeterministicSemanticPulseAdapter:
    """Contract adapter: proposes work and never commits or calls a provider."""

    proposal_kind: str = "shadow.task-proposal"
    calls: int = 0

    def propose(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {
            "proposal_id": request["proposal_id"],
            "proposal_kind": self.proposal_kind,
            "input_schema_ref": request["input_schema_ref"],
            "typed_payload": request["typed_payload"],
            "principal_ref": request["principal_ref"],
            "space_id": request["space_id"],
            "evidence_refs": list(request["evidence_refs"]),
            "budget": dict(request["budget"]),
            "cooldown_key": request["cooldown_key"],
            "expires_at": request["expires_at"],
            "idempotency_key": request["idempotency_key"],
        }
