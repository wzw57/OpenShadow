from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.adapters import AdapterRegistry, CapabilityRequirement, ExecutionBinding
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.registry import ContractRegistry

ROUTING_SCHEMA = "https://schemas.openshadow.dev/contracts/routing/1.0.0"
POLICY_DECISION_SCHEMA = f"{ROUTING_SCHEMA}#/$defs/PolicyDecision"
BINDING_PROPOSAL_SCHEMA = f"{ROUTING_SCHEMA}#/$defs/BindingProposal"


class PolicyEngine(Protocol):
    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]: ...


class RouterAdapter(Protocol):
    def propose(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PolicyDecisionResult:
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BindingProposalResult:
    payload: dict[str, Any]


class RoutingPolicyService:
    """Core-side validation for external PolicyDecision and BindingProposal values."""

    def __init__(
        self,
        registry: ContractRegistry,
        adapters: AdapterRegistry,
        policy_engine: PolicyEngine,
        router: RouterAdapter,
    ) -> None:
        self.registry = registry
        self.adapters = adapters
        self.policy_engine = policy_engine
        self.router = router

    def evaluate_policy(self, request: dict[str, Any]) -> PolicyDecisionResult:
        proposed = self.policy_engine.evaluate(dict(request))
        self._validate(proposed, POLICY_DECISION_SCHEMA)
        self._check_policy_decision(request, proposed)
        return PolicyDecisionResult(proposed)

    def propose_binding(
        self,
        *,
        request: dict[str, Any],
        policy_decision: dict[str, Any],
    ) -> BindingProposalResult:
        self._validate(policy_decision, POLICY_DECISION_SCHEMA)
        self._check_policy_decision(request, policy_decision)
        proposed = self.router.propose(dict(request))
        self._validate(proposed, BINDING_PROPOSAL_SCHEMA)
        if proposed["policy_decision_ref"] != request["policy_decision_ref"]:
            raise _error("shadow.router.binding-invalid", "Binding proposal references a different Policy Decision.")
        if proposed["required_capabilities"] != request["required_capabilities"]:
            raise _error("shadow.policy.capability-missing", "Router cannot change required capabilities.", category="unauthorized")
        if not self._scope_equal_or_narrower(proposed["requested_data_scope"], request["requested_data_scope"]):
            raise _error("shadow.policy.scope-expansion", "Router cannot expand requested data scope.", category="unauthorized")
        return BindingProposalResult(proposed)

    def accept_binding(
        self,
        *,
        proposal: dict[str, Any],
        policy_decision: dict[str, Any],
        scope_ref: dict[str, str],
        capability_envelope_ref: dict[str, Any],
        selection_source_ref: dict[str, str],
        binding_id: str,
    ) -> ExecutionBinding:
        self._validate(proposal, BINDING_PROPOSAL_SCHEMA)
        self._validate(policy_decision, POLICY_DECISION_SCHEMA)
        if policy_decision["decision"] != "allow":
            raise _error("shadow.policy.denied", "Only an allowed Policy Decision can create a Binding.", category="unauthorized")
        if policy_decision["revocation_state"] != "active":
            raise _error("shadow.policy.expired", "Policy Decision is revoked or unknown.", category="conflict")
        if policy_decision["effective_until"] <= datetime.now(UTC).isoformat().replace("+00:00", "Z"):
            raise _error("shadow.policy.expired", "Policy Decision has expired.", category="conflict")
        allowed = set(policy_decision["allowed_capabilities"])
        missing = sorted(set(proposal["required_capabilities"]) - allowed)
        if missing:
            raise _error("shadow.policy.capability-missing", "Policy does not allow required capabilities.", {"capabilities": missing}, category="unauthorized")
        requirements = [CapabilityRequirement(capability_id=capability, version_range="*") for capability in proposal["required_capabilities"]]
        try:
            return self.adapters.bind(
                descriptor_id=proposal["adapter_ref"]["record_id"],
                target_kind=proposal["target_kind"],
                required_capabilities=requirements,
                binding_id=binding_id,
                scope_ref=scope_ref,
                capability_envelope_ref=capability_envelope_ref,
                selection_source_ref=selection_source_ref,
            )
        except ShadowDomainError as exc:
            raise _error("shadow.router.binding-invalid", exc.error.message, category=exc.error.category) from exc

    def _check_policy_decision(self, request: dict[str, Any], decision: dict[str, Any]) -> None:
        if decision["decision"] == "deny":
            raise _error("shadow.policy.denied", "Policy denied the requested operation.", category="unauthorized")
        if decision["revocation_state"] != "active":
            raise _error("shadow.policy.expired", "Policy Decision is not active.", category="conflict")
        try:
            effective_until = datetime.fromisoformat(decision["effective_until"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise _error("shadow.policy.expired", "Policy Decision expiry is invalid.") from exc
        if effective_until <= datetime.now(UTC):
            raise _error("shadow.policy.expired", "Policy Decision has expired.", category="conflict")
        missing = sorted(set(request.get("required_capabilities", [])) - set(decision["allowed_capabilities"]))
        if missing:
            raise _error("shadow.policy.capability-missing", "Policy does not allow requested capabilities.", {"capabilities": missing}, category="unauthorized")
        requested_effects = set(request.get("allowed_side_effects", request.get("requested_side_effects", [])))
        if not requested_effects.issubset(set(decision["allowed_side_effects"])):
            raise _error("shadow.policy.scope-expansion", "Requested side effects exceed Policy Decision.", category="unauthorized")
        if not self._scope_equal_or_narrower(request.get("requested_data_scope", {}), decision["data_scope"]):
            raise _error("shadow.policy.scope-expansion", "Requested data scope exceeds Policy Decision.", category="unauthorized")

    @staticmethod
    def _scope_equal_or_narrower(candidate: dict[str, Any], allowed: dict[str, Any]) -> bool:
        for key, value in candidate.items():
            if key not in allowed:
                return False
            permitted = allowed[key]
            if isinstance(value, list):
                if not set(value).issubset(set(permitted if isinstance(permitted, list) else [])):
                    return False
            elif isinstance(value, dict):
                if not isinstance(permitted, dict) or not RoutingPolicyService._scope_equal_or_narrower(value, permitted):
                    return False
            elif value != permitted:
                return False
        return True

    def _validate(self, payload: dict[str, Any], schema: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error("shadow.router.binding-invalid", "Routing payload does not satisfy its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))
