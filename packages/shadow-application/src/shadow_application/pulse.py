from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.admission import AdmissionResult, AdmissionService
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry

PULSE_SCHEMA = "https://schemas.openshadow.dev/contracts/pulse/1.0.0"
TRIGGER_SCHEMA = f"{PULSE_SCHEMA}#/$defs/PulseTrigger"
OBSERVATION_SCHEMA = f"{PULSE_SCHEMA}#/$defs/PulseObservation"
PROPOSAL_SCHEMA = f"{PULSE_SCHEMA}#/$defs/PulseProposal"


class SemanticPulseAdapter(Protocol):
    def propose(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PulseProposalResult:
    proposal: dict[str, Any]
    replayed: bool = False


class SemanticPulseService:
    """Optional proposal producer; work always re-enters the existing Admission boundary."""

    def __init__(self, registry: ContractRegistry, adapter: SemanticPulseAdapter) -> None:
        self.registry = registry
        self.adapter = adapter

    def produce_proposal(
        self,
        *,
        trigger: dict[str, Any],
        observation: dict[str, Any],
        proposal_kind: str,
        input_schema_ref: str,
        typed_payload: dict[str, Any],
        budget: dict[str, Any],
        cooldown_key: str,
        expires_at: str,
        idempotency_key: str,
    ) -> PulseProposalResult:
        self._validate(trigger, TRIGGER_SCHEMA)
        self._validate(observation, OBSERVATION_SCHEMA)
        if observation["source_status"] != "available":
            raise _error("shadow.pulse.source-unavailable", "Pulse source is unavailable or unknown.", category="unavailable")
        self._check_expiry(expires_at)
        self._check_budget(budget)
        request = {
            "trigger": trigger,
            "observation": observation,
            "proposal_id": f"pulse-proposal-{sha256_digest({'trigger': trigger, 'observation': observation, 'kind': proposal_kind, 'payload': typed_payload, 'key': idempotency_key})[7:39]}",
            "proposal_kind": proposal_kind,
            "input_schema_ref": input_schema_ref,
            "typed_payload": typed_payload,
            "principal_ref": trigger["principal_ref"],
            "space_id": trigger["space_id"],
            "evidence_refs": observation["evidence_refs"],
            "budget": budget,
            "cooldown_key": cooldown_key,
            "expires_at": expires_at,
            "idempotency_key": idempotency_key,
        }
        proposal = self.adapter.propose(request)
        self._validate(proposal, PROPOSAL_SCHEMA)
        if proposal["principal_ref"] != trigger["principal_ref"] or proposal["space_id"] != trigger["space_id"]:
            raise _error("shadow.pulse.unauthorized", "Pulse adapter cannot change owner or space.", category="unauthorized")
        if proposal["idempotency_key"] != idempotency_key:
            raise _error("shadow.pulse.invalid-proposal", "Pulse adapter cannot change idempotency key.")
        if proposal["proposal_id"] != request["proposal_id"]:
            raise _error("shadow.pulse.invalid-proposal", "Pulse adapter cannot change stable proposal identity.")
        return PulseProposalResult(proposal)

    def admit_proposal(
        self,
        *,
        proposal: dict[str, Any],
        endpoint_ref: str,
        admission: AdmissionService,
        required_capabilities: list[str] | None = None,
        acceptable_target_kinds: list[str] | None = None,
    ) -> AdmissionResult:
        self._validate(proposal, PROPOSAL_SCHEMA)
        self._check_expiry(proposal["expires_at"])
        return admission.admit(
            request_type="shadow.semantic-pulse",
            input_type=proposal["proposal_kind"],
            work_input={
                "schema_ref": proposal["input_schema_ref"],
                "typed_input": {"pulse_proposal": proposal},
            },
            principal_ref=proposal["principal_ref"],
            endpoint_ref=endpoint_ref,
            space_id=proposal["space_id"],
            required_capabilities=required_capabilities or [],
            acceptable_target_kinds=acceptable_target_kinds,
            idempotency_key=proposal["idempotency_key"],
        )

    def _validate(self, payload: dict[str, Any], schema: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error("shadow.pulse.invalid-proposal", "Pulse payload does not satisfy its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc

    @staticmethod
    def _check_expiry(value: str) -> None:
        try:
            expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise _error("shadow.pulse.expired", "Pulse expiry is invalid.") from exc
        if expiry <= datetime.now(UTC):
            raise _error("shadow.pulse.expired", "Pulse proposal has expired.", category="conflict")

    @staticmethod
    def _check_budget(budget: dict[str, Any]) -> None:
        max_cost = budget.get("max_cost")
        if max_cost is not None and (not isinstance(max_cost, (int, float)) or max_cost <= 0):
            raise _error("shadow.pulse.budget-exhausted", "Pulse budget is exhausted.", category="conflict")


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))
