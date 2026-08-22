from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeterministicPolicyEngine:
    decision: str = "allow"
    policy_ref: str = "policy-default"
    policy_version: int = 1

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "policy_ref": {"record_id": self.policy_ref, "version": self.policy_version},
            "policy_version": self.policy_version,
            "evaluated_at": "2026-08-22T08:00:00Z",
            "effective_until": "2099-01-01T00:00:00Z",
            "allowed_capabilities": list(request.get("required_capabilities", [])),
            "data_scope": dict(request.get("requested_data_scope", {})),
            "resource_scope": dict(request.get("requested_resource_scope", {})),
            "budget_limits": dict(request.get("budget_limits", {})),
            "allowed_side_effects": list(request.get("requested_side_effects", ["none"])),
            "approval_refs": list(request.get("approval_refs", [])),
            "revocation_state": "active",
            "reason_code": "deterministic.policy",
        }


@dataclass(slots=True)
class DeterministicRouterAdapter:
    target_kind: str = "vendor.example-runtime"
    adapter_id: str = "adapter-deterministic"
    contract_version: str = "1.0.0"

    def propose(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "proposal_id": request["proposal_id"],
            "subject_ref": request["subject_ref"],
            "target_kind": self.target_kind,
            "adapter_ref": {"record_id": self.adapter_id, "version": 1},
            "contract_version": self.contract_version,
            "required_capabilities": list(request.get("required_capabilities", [])),
            "requested_data_scope": dict(request.get("requested_data_scope", {})),
            "policy_decision_ref": request["policy_decision_ref"],
            "candidate_rank": 0,
            "fallback": False,
            "proposed_at": "2026-08-22T08:00:00Z",
            "idempotency_key": request["idempotency_key"],
            "reason": "deterministic adapter match",
        }
