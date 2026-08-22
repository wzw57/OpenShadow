from __future__ import annotations

from pathlib import Path

import pytest
from shadow_adapters import DeterministicPolicyEngine, DeterministicRouterAdapter
from shadow_application import RoutingPolicyService
from shadow_kernel.adapters import AdapterDescriptor, AdapterRegistry
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]


def _service(*, router: DeterministicRouterAdapter | None = None, decision: str = "allow") -> RoutingPolicyService:
    descriptor_body = {
        "descriptor_id": "adapter-deterministic",
        "descriptor_version": "1.0.0",
        "adapter_family": "shadow.execution",
        "implementation_ref": "deterministic://router",
        "implementation_version": "1.0.0",
        "supported_contracts": [{"contract_id": "shadow.execution", "version_range": "1.0.0"}],
        "supported_target_kinds": ["vendor.example-runtime"],
        "capabilities": [
            {
                "capability_id": "shadow.action.notify",
                "capability_version": "1.0.0",
                "contract_ref": "https://schemas.openshadow.dev/contracts/action/1.0.0",
            }
        ],
        "config_schema_ref": "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor",
    }
    adapters = AdapterRegistry()
    adapters.register(AdapterDescriptor(**descriptor_body, descriptor_digest=sha256_digest(descriptor_body)))
    return RoutingPolicyService(
        ContractRegistry(ROOT),
        adapters,
        DeterministicPolicyEngine(decision=decision),
        router or DeterministicRouterAdapter(),
    )


def _request() -> dict[str, object]:
    return {
        "required_capabilities": ["shadow.action.notify"],
        "requested_data_scope": {"classification_max": "personal"},
        "requested_resource_scope": {"space_id": "space-routing"},
        "budget_limits": {"max_cost": 10},
        "requested_side_effects": ["low"],
        "approval_refs": [],
    }


def test_policy_decision_and_binding_proposal_are_external_outputs_only() -> None:
    service = _service()
    request = _request()
    decision = service.evaluate_policy(request).payload
    assert decision["decision"] == "allow"
    binding_request = {
        **request,
        "proposal_id": "binding-proposal-test",
        "subject_ref": {"record_id": "run-routing", "version": 1},
        "policy_decision_ref": {"record_id": "policy-default", "version": 1},
        "idempotency_key": "binding-test",
    }
    proposal = service.propose_binding(request=binding_request, policy_decision=decision).payload
    assert proposal["target_kind"] == "vendor.example-runtime"
    assert proposal["adapter_ref"]["record_id"] == "adapter-deterministic"
    assert proposal["required_capabilities"] == request["required_capabilities"]


def test_core_accepts_binding_only_after_final_capability_and_policy_checks() -> None:
    service = _service()
    request = {
        **_request(),
        "proposal_id": "binding-proposal-test",
        "subject_ref": {"record_id": "run-routing", "version": 1},
        "policy_decision_ref": {"record_id": "policy-default", "version": 1},
        "idempotency_key": "binding-test",
    }
    decision = service.evaluate_policy(request).payload
    proposal = service.propose_binding(request=request, policy_decision=decision).payload
    binding = service.accept_binding(
        proposal=proposal,
        policy_decision=decision,
        scope_ref={"record_id": "run-routing"},
        capability_envelope_ref={"record_id": "envelope-routing", "version": 1},
        selection_source_ref={"record_id": "binding-proposal-test"},
        binding_id="binding-routing",
    )
    assert binding.target_kind == "vendor.example-runtime"
    assert binding.resolved_capabilities[0].satisfied is True


def test_policy_deny_scope_expansion_and_unknown_target_are_rejected() -> None:
    with pytest.raises(ShadowDomainError) as denied:
        service = _service(decision="deny")
        service.evaluate_policy(_request())
    assert denied.value.error.code == "shadow.policy.denied"

    class ExpandingRouter(DeterministicRouterAdapter):
        def propose(self, request: dict[str, object]) -> dict[str, object]:
            result = super().propose(request)
            result["requested_data_scope"] = {"classification_max": "restricted"}
            return result

    service = _service(router=ExpandingRouter())
    request = {
        **_request(),
        "proposal_id": "binding-proposal-expanding",
        "subject_ref": {"record_id": "run-routing", "version": 1},
        "policy_decision_ref": {"record_id": "policy-default", "version": 1},
        "idempotency_key": "binding-expanding",
    }
    decision = service.evaluate_policy(request).payload
    with pytest.raises(ShadowDomainError) as expansion:
        service.propose_binding(request=request, policy_decision=decision)
    assert expansion.value.error.code == "shadow.policy.scope-expansion"

def test_unsupported_target_fails_at_core_acceptance() -> None:
    service = _service()
    request = {
        **_request(),
        "proposal_id": "binding-proposal-target",
        "subject_ref": {"record_id": "run-routing", "version": 1},
        "policy_decision_ref": {"record_id": "policy-default", "version": 1},
        "idempotency_key": "binding-target",
    }
    decision = service.evaluate_policy(request).payload
    proposal = service.propose_binding(request=request, policy_decision=decision).payload
    proposal["target_kind"] = "vendor.unknown-target"
    with pytest.raises(ShadowDomainError) as error:
        service.accept_binding(
            proposal=proposal,
            policy_decision=decision,
            scope_ref={"record_id": "run-routing"},
            capability_envelope_ref={"record_id": "envelope-routing", "version": 1},
            selection_source_ref={"record_id": "binding-proposal-target"},
            binding_id="binding-routing",
        )
    assert error.value.error.code == "shadow.router.binding-invalid"
