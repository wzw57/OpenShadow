from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

ACTION_SCHEMA = "https://schemas.openshadow.dev/contracts/action/1.0.0"
ACTION_PAYLOAD_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ActionPayload"
ACTION_PROPOSAL_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ActionProposalPayload"
APPROVAL_PROPOSAL_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ApprovalProposalPayload"
ACTION_PROPOSAL_RECORD_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ActionProposalRecordPayload"
APPROVAL_PROPOSAL_RECORD_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ActionApprovalProposalRecordPayload"
PROVIDER_RESULT_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ProviderResultPayload"
RECONCILIATION_SCHEMA = f"{ACTION_SCHEMA}#/$defs/ReconciliationPayload"
ACTION_RECORD_TYPE = "shadow.profile.action"
PROPOSAL_RECORD_TYPE = "shadow.proposal"
RESULT_RECORD_TYPE = "shadow.action.provider-result"
RECONCILIATION_RECORD_TYPE = "shadow.action.reconciliation"
RETENTION_REF = StableRecordRef(record_id="retention-default")
SUPPORTED_CAPABILITIES = {"shadow.action.notify", "shadow.action.lookup"}


class ActionProvider(Protocol):
    def execute(self, action: dict[str, Any]) -> dict[str, Any]: ...

    def reconcile(self, action: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ActionProposalCandidate:
    proposal_id: str
    submitted_by: str
    owner_ref: str
    space_id: str
    proposal_type: str
    payload: dict[str, Any]


class ActionService:
    """Proposal/Commit and lifecycle boundary for the Phase 4 Action Profile."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
        *,
        supported_capabilities: set[str] | None = None,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry
        self.supported_capabilities = supported_capabilities or SUPPORTED_CAPABILITIES

    def propose_action(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        action_kind: str,
        target_ref: dict[str, Any],
        typed_parameters: dict[str, Any],
        data_classification: str,
        side_effect_level: str,
        required_capabilities: list[str],
        deadline: str,
        secret_refs: list[str] | None = None,
        provider_target_kind: str | None = None,
        proposal_reason: str | None = None,
    ) -> ActionProposalCandidate:
        proposal: dict[str, Any] = {
            "proposed_operation": "create",
            "action_kind": action_kind,
            "target_ref": target_ref,
            "typed_parameters": typed_parameters,
            "data_classification": data_classification,
            "side_effect_level": side_effect_level,
            "required_capabilities": required_capabilities,
            "deadline": deadline,
            "secret_refs": secret_refs or [],
        }
        if provider_target_kind is not None:
            proposal["provider_target_kind"] = provider_target_kind
        if proposal_reason:
            proposal["proposal_reason"] = proposal_reason
        self._validate(proposal, ACTION_PROPOSAL_SCHEMA, "shadow.action.operation-invalid")
        proposal_id = f"proposal-{sha256_digest({'owner': owner_ref, 'space': space_id, 'proposal': proposal})[7:39]}"
        return ActionProposalCandidate(
            proposal_id=proposal_id,
            submitted_by=submitted_by,
            owner_ref=owner_ref,
            space_id=space_id,
            proposal_type="shadow.action-proposal",
            payload=proposal,
        )

    def propose_approval(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        action_id: str,
        expected_version: int,
        approver_ref: str,
        decision: str,
        evidence_refs: list[dict[str, Any]],
        proposal_reason: str | None = None,
    ) -> ActionProposalCandidate:
        action = self._load_action(
            action_id,
            owner_ref=owner_ref,
            space_id=space_id,
            expected_version=expected_version,
            lifecycle="approval_required",
        )
        del action
        operation = "approve" if decision == "approved" else "reject" if decision == "rejected" else decision
        proposal: dict[str, Any] = {
            "proposed_operation": operation,
            "action_ref": {"record_id": action_id},
            "expected_version": expected_version,
            "approver_ref": approver_ref,
            "decision": decision,
            "evidence_refs": evidence_refs,
        }
        if proposal_reason:
            proposal["proposal_reason"] = proposal_reason
        self._validate(proposal, APPROVAL_PROPOSAL_SCHEMA, "shadow.action.operation-invalid")
        proposal_id = f"proposal-{sha256_digest({'owner': owner_ref, 'space': space_id, 'proposal': proposal})[7:39]}"
        return ActionProposalCandidate(
            proposal_id=proposal_id,
            submitted_by=submitted_by,
            owner_ref=owner_ref,
            space_id=space_id,
            proposal_type="shadow.action-approval-proposal",
            payload=proposal,
        )

    def submit_proposal(self, candidate: ActionProposalCandidate, *, idempotency_key: str) -> dict[str, Any]:
        self._require_available()
        schema = (
            ACTION_PROPOSAL_RECORD_SCHEMA
            if candidate.proposal_type == "shadow.action-proposal"
            else APPROVAL_PROPOSAL_RECORD_SCHEMA
        )
        payload = {
            "proposal_type": candidate.proposal_type,
            "status": "pending",
            "proposer_ref": candidate.submitted_by,
            "owner_ref": candidate.owner_ref,
            "space_id": candidate.space_id,
            "proposal": candidate.payload,
        }
        operation = self._proposal_operation(
            operation_id=f"operation-{candidate.proposal_id}-create",
            operation="create",
            proposal_id=candidate.proposal_id,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            created_by=candidate.submitted_by,
            typed_payload=payload,
            schema=schema,
        )
        result = self._commit(
            [operation],
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(candidate.payload),
            commit_request_id=f"commit-request-{candidate.proposal_id}",
            actor_ref=candidate.submitted_by,
        )
        return self._record_from_result(result, candidate.proposal_id)

    def accept_proposal(
        self,
        *,
        proposal_id: str,
        proposal_expected_version: int,
        principal_ref: str,
        space_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        proposal_record = self.repository.get(proposal_id)
        if proposal_record is None:
            raise _error("shadow.action.not-found", "Action Proposal was not found.")
        self._assert_boundary(proposal_record, principal_ref, space_id)
        typed_payload = proposal_record.get("typed_payload", {})
        proposal_type = typed_payload.get("proposal_type")
        if proposal_type not in {"shadow.action-proposal", "shadow.action-approval-proposal"}:
            raise _invalid("Target record is not an Action Proposal.")
        request_digest = sha256_digest(
            {"proposal_id": proposal_id, "proposal": typed_payload.get("proposal"), "expected": proposal_expected_version}
        )
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            action_result = next(
                (item for item in prior["result"].operation_results if item.record_id.startswith("action-")),
                None,
            )
            if action_result and action_result.resulting_version:
                return {
                    "decision": "accepted",
                    "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
                    "action_ref": {"record_id": action_result.record_id, "version": action_result.resulting_version},
                    "replayed": True,
                    "record": self.get_action(action_result.record_id, principal_ref, space_id),
                }
        if typed_payload.get("status") != "pending":
            raise _error("shadow.action.invalid-transition", "Action Proposal is no longer pending.", category="conflict")
        if proposal_type == "shadow.action-proposal":
            return self._accept_action_proposal(
                proposal_record,
                proposal_id=proposal_id,
                proposal_expected_version=proposal_expected_version,
                principal_ref=principal_ref,
                space_id=space_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
        return self._accept_approval_proposal(
            proposal_record,
            proposal_id=proposal_id,
            proposal_expected_version=proposal_expected_version,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
        )

    def begin_execution(
        self,
        *,
        action_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        request_digest = sha256_digest({"action": action_id, "expected_version": expected_version, "operation": "execute"})
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            return {"record": self.get_action(action_id, principal_ref, space_id), "replayed": True}
        action = self._load_action(
            action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            expected_version=expected_version,
            lifecycle="approved",
        )
        payload = deepcopy(action["typed_payload"])
        payload["lifecycle"] = "executing"
        operation = self._action_operation(
            operation_id=f"operation-{action_id}-execute",
            action_id=action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=payload,
            expected_version=expected_version,
            origin_ref=action_id,
        )
        result = self._commit(
            [operation], owner_ref=principal_ref, space_id=space_id, idempotency_key=idempotency_key,
            request_digest=request_digest, commit_request_id=f"commit-request-{action_id}-execute", actor_ref=principal_ref,
        )
        return {"record": self._record_from_result(result, action_id), "replayed": result.outcome == "idempotent_replay"}

    def record_provider_result(
        self,
        *,
        action_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        outcome: str,
        idempotency_key: str,
        observed_at: str,
        external_ref: str | None = None,
        failure_summary: dict[str, Any] | None = None,
        unknown_reason: str | None = None,
        provider_digest: str | None = None,
    ) -> dict[str, Any]:
        self._require_available()
        result_payload: dict[str, Any] = {
            "action_ref": {"record_id": action_id},
            "expected_version": expected_version,
            "outcome": outcome,
            "observed_at": observed_at,
        }
        for key, value in (("external_ref", external_ref), ("failure_summary", failure_summary), ("unknown_reason", unknown_reason), ("provider_digest", provider_digest)):
            if value is not None:
                result_payload[key] = value
        self._validate(result_payload, PROVIDER_RESULT_SCHEMA, "shadow.action.result-invalid")
        request_digest = sha256_digest(result_payload)
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            result_record = next(
                (item for item in prior["result"].operation_results if item.record_id.startswith("action-result-")),
                None,
            )
            return {
                "result": self._record_from_operation(result_record) if result_record else None,
                "record": self.get_action(action_id, principal_ref, space_id),
                "replayed": True,
            }
        action = self._load_action(
            action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            expected_version=expected_version,
            lifecycle="executing",
        )
        payload = self._result_payload(action["typed_payload"], outcome, external_ref, failure_summary, unknown_reason)
        result_id = f"action-result-{sha256_digest({'action': action_id, 'payload': result_payload})[7:39]}"
        result_operation = CommitOperation(
            operation_id=f"operation-{result_id}-create",
            operation="create",
            record_id=result_id,
            record_type=RESULT_RECORD_TYPE,
            target_schema_ref=PROVIDER_RESULT_SCHEMA,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.action-provider", origin_ref=action_id),
            retention_policy_ref=RETENTION_REF,
            typed_payload=result_payload,
        )
        action_operation = self._action_operation(
            operation_id=f"operation-{action_id}-result",
            action_id=action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=payload,
            expected_version=expected_version,
            origin_ref=result_id,
        )
        result = self._commit(
            [result_operation, action_operation], owner_ref=principal_ref, space_id=space_id,
            idempotency_key=idempotency_key, request_digest=request_digest,
            commit_request_id=f"commit-request-{result_id}", actor_ref=principal_ref,
        )
        return {
            "result": self._record_from_result(result, result_id),
            "record": self._record_from_result(result, action_id),
            "replayed": result.outcome == "idempotent_replay",
        }

    def reconcile_unknown(
        self,
        *,
        action_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        outcome: str,
        evidence_refs: list[dict[str, Any]],
        observed_at: str,
        idempotency_key: str,
        external_ref: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._require_available()
        reconciliation_payload: dict[str, Any] = {
            "action_ref": {"record_id": action_id},
            "expected_version": expected_version,
            "outcome": outcome,
            "evidence_refs": evidence_refs,
            "observed_at": observed_at,
        }
        if external_ref is not None:
            reconciliation_payload["external_ref"] = external_ref
        if reason is not None:
            reconciliation_payload["reason"] = reason
        self._validate(reconciliation_payload, RECONCILIATION_SCHEMA, "shadow.action.reconciliation-invalid")
        request_digest = sha256_digest(reconciliation_payload)
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            recon_result = next(
                (item for item in prior["result"].operation_results if item.record_id.startswith("reconciliation-")),
                None,
            )
            return {
                "reconciliation": self._record_from_operation(recon_result) if recon_result else None,
                "record": self.get_action(action_id, principal_ref, space_id),
                "replayed": True,
            }
        action = self._load_action(
            action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            expected_version=expected_version,
            lifecycle="unknown",
        )
        payload = self._result_payload(action["typed_payload"], outcome, external_ref, None, reason)
        recon_id = f"reconciliation-{sha256_digest({'action': action_id, 'payload': reconciliation_payload})[7:39]}"
        recon_operation = CommitOperation(
            operation_id=f"operation-{recon_id}-create",
            operation="create",
            record_id=recon_id,
            record_type=RECONCILIATION_RECORD_TYPE,
            target_schema_ref=RECONCILIATION_SCHEMA,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.action-reconciliation", origin_ref=action_id),
            retention_policy_ref=RETENTION_REF,
            typed_payload=reconciliation_payload,
        )
        payload.setdefault("reconciliation_refs", []).append({"record_id": recon_id, "version": 1})
        action_operation = self._action_operation(
            operation_id=f"operation-{action_id}-reconcile",
            action_id=action_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=payload,
            expected_version=expected_version,
            origin_ref=recon_id,
        )
        result = self._commit(
            [recon_operation, action_operation], owner_ref=principal_ref, space_id=space_id,
            idempotency_key=idempotency_key, request_digest=request_digest,
            commit_request_id=f"commit-request-{recon_id}", actor_ref=principal_ref,
        )
        return {
            "reconciliation": self._record_from_result(result, recon_id),
            "record": self._record_from_result(result, action_id),
            "replayed": result.outcome == "idempotent_replay",
        }

    def list_actions(self, *, owner_ref: str | None, space_id: str, limit: int = 50) -> list[dict[str, Any]]:
        records = self.repository.query_heads(
            owner_refs={owner_ref} if owner_ref else None,
            space_ids={space_id},
            record_types={ACTION_RECORD_TYPE},
            record_states={"active", "logically_deleted", "erased"},
            limit=None,
        )
        return sorted(records, key=lambda item: item["record_id"])[:limit]

    def get_action(self, action_id: str, principal_ref: str | None = None, space_id: str | None = None, enforce_owner: bool = True) -> dict[str, Any] | None:
        record = self.repository.get(action_id)
        if record is None or record["record_type"] != ACTION_RECORD_TYPE:
            return None
        if principal_ref is not None and space_id is not None and enforce_owner:
            self._assert_boundary(record, principal_ref, space_id)
        elif space_id is not None and record["space_id"] != space_id:
            raise _error("shadow.action.space-mismatch", "Action does not belong to the requested Space.", category="unauthorized")
        return record

    def _accept_action_proposal(
        self, proposal_record: dict[str, Any], *, proposal_id: str, proposal_expected_version: int,
        principal_ref: str, space_id: str, idempotency_key: str, request_digest: str,
    ) -> dict[str, Any]:
        proposal = proposal_record["typed_payload"]["proposal"]
        self._check_policy(proposal)
        action_id = f"action-{sha256_digest({'owner': principal_ref, 'space': space_id, 'proposal_id': proposal_id})[7:39]}"
        if self.repository.get(action_id) is not None:
            raise _error("shadow.repository.expected-version-conflict", "An Action already exists for this Proposal.", category="conflict")
        lifecycle = "approval_required" if proposal["side_effect_level"] == "medium" else "approved"
        action_payload = {
            "action_kind": proposal["action_kind"],
            "target_ref": proposal["target_ref"],
            "typed_parameters": proposal["typed_parameters"],
            "data_classification": proposal["data_classification"],
            "side_effect_level": proposal["side_effect_level"],
            "required_capabilities": proposal["required_capabilities"],
            "deadline": proposal["deadline"],
            "secret_refs": proposal["secret_refs"],
            "lifecycle": lifecycle,
            "idempotency_key": idempotency_key,
            "policy_decision": "approval_required" if lifecycle == "approval_required" else "auto_approved",
        }
        if "provider_target_kind" in proposal:
            action_payload["provider_target_kind"] = proposal["provider_target_kind"]
        self._validate(action_payload, ACTION_PAYLOAD_SCHEMA, "shadow.action.operation-invalid")
        action_operation = self._action_operation(
            operation_id=f"operation-{action_id}-create", action_id=action_id, owner_ref=principal_ref,
            space_id=space_id, created_by=principal_ref, typed_payload=action_payload,
            expected_version=None, origin_ref=proposal_id, operation="create",
        )
        accepted_payload = deepcopy(proposal_record["typed_payload"])
        accepted_payload["status"] = "accepted"
        accepted_payload["resulting_action_ref"] = {"record_id": action_id}
        proposal_operation = self._proposal_operation(
            operation_id=f"operation-{proposal_id}-accept", operation="update", proposal_id=proposal_id,
            owner_ref=principal_ref, space_id=space_id, created_by=principal_ref,
            typed_payload=accepted_payload, expected_version=proposal_expected_version,
            schema=ACTION_PROPOSAL_RECORD_SCHEMA,
        )
        result = self._commit(
            [proposal_operation, action_operation], owner_ref=principal_ref, space_id=space_id,
            idempotency_key=idempotency_key, request_digest=request_digest,
            commit_request_id=f"commit-request-{proposal_id}-accept", actor_ref=principal_ref,
        )
        operation_result = next(item for item in result.operation_results if item.record_id == action_id)
        if operation_result.resulting_version is None:
            raise _error("shadow.repository.record-missing", "Accepted Action has no resulting version.")
        return {
            "decision": "accepted",
            "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
            "action_ref": {"record_id": action_id, "version": operation_result.resulting_version},
            "replayed": result.outcome == "idempotent_replay",
            "record": self.get_action(action_id, principal_ref, space_id),
        }

    def _accept_approval_proposal(
        self, proposal_record: dict[str, Any], *, proposal_id: str, proposal_expected_version: int,
        principal_ref: str, space_id: str, idempotency_key: str, request_digest: str,
    ) -> dict[str, Any]:
        proposal = proposal_record["typed_payload"]["proposal"]
        action_id = proposal["action_ref"]["record_id"]
        action = self._load_action(
            action_id, owner_ref=principal_ref, space_id=space_id,
            expected_version=proposal["expected_version"], lifecycle="approval_required",
        )
        action_payload = deepcopy(action["typed_payload"])
        if proposal["decision"] == "approved":
            action_payload["lifecycle"] = "approved"
            action_payload["policy_decision"] = "auto_approved"
            action_payload["approval_ref"] = {"record_id": proposal_id, "version": proposal_expected_version + 1}
        else:
            action_payload["lifecycle"] = "failed"
            action_payload["failure_summary"] = {"code": "shadow.action.approval-rejected", "approver_ref": proposal["approver_ref"]}
        action_operation = self._action_operation(
            operation_id=f"operation-{action_id}-approval", action_id=action_id, owner_ref=principal_ref,
            space_id=space_id, created_by=principal_ref, typed_payload=action_payload,
            expected_version=proposal["expected_version"], origin_ref=proposal_id,
        )
        accepted_payload = deepcopy(proposal_record["typed_payload"])
        accepted_payload["status"] = "accepted"
        accepted_payload["resulting_action_ref"] = {"record_id": action_id}
        proposal_operation = self._proposal_operation(
            operation_id=f"operation-{proposal_id}-accept", operation="update", proposal_id=proposal_id,
            owner_ref=principal_ref, space_id=space_id, created_by=principal_ref,
            typed_payload=accepted_payload, expected_version=proposal_expected_version,
            schema=APPROVAL_PROPOSAL_RECORD_SCHEMA,
        )
        result = self._commit(
            [proposal_operation, action_operation], owner_ref=principal_ref, space_id=space_id,
            idempotency_key=idempotency_key, request_digest=request_digest,
            commit_request_id=f"commit-request-{proposal_id}-accept", actor_ref=principal_ref,
        )
        return {
            "decision": "accepted",
            "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
            "action_ref": {"record_id": action_id, "version": (action["version"] + 1)},
            "replayed": result.outcome == "idempotent_replay",
            "record": self.get_action(action_id, principal_ref, space_id),
        }

    def _check_policy(self, proposal: dict[str, Any]) -> None:
        if proposal["side_effect_level"] == "high":
            raise _error("shadow.action.policy-denied", "High-risk Action is denied by the deterministic policy.", category="unauthorized")
        unknown = sorted(set(proposal["required_capabilities"]) - self.supported_capabilities)
        if unknown:
            raise _error("shadow.action.capability-unsupported", "Action requires unsupported capabilities.", {"capabilities": unknown}, category="incompatible")
        try:
            deadline = datetime.fromisoformat(proposal["deadline"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid("Action deadline is invalid.") from exc
        if deadline <= datetime.now(UTC):
            raise _error("shadow.action.policy-denied", "Action deadline has expired.", category="conflict")

    def _load_action(
        self, action_id: str, *, owner_ref: str, space_id: str,
        expected_version: int | None = None, lifecycle: str | None = None,
    ) -> dict[str, Any]:
        head = self.repository.get(action_id)
        if head is None or head["record_type"] != ACTION_RECORD_TYPE:
            raise _error("shadow.action.not-found", "Action was not found.", {"record_id": action_id})
        self._assert_boundary(head, owner_ref, space_id)
        if head["record_state"] != "active":
            raise _error("shadow.action.deleted-head", "Action head is not active.", category="conflict")
        if expected_version is not None and head["version"] != expected_version:
            raise _error("shadow.repository.expected-version-conflict", "Action expected version does not match the current head.", {"record_id": action_id, "expected_version": expected_version, "current_version": head["version"]}, category="conflict")
        if lifecycle is not None and head["typed_payload"].get("lifecycle") != lifecycle:
            raise _error("shadow.action.invalid-transition", f"Action is not in {lifecycle} state.", {"lifecycle": head["typed_payload"].get("lifecycle")}, category="conflict")
        return head

    @staticmethod
    def _result_payload(current: dict[str, Any], outcome: str, external_ref: str | None, failure_summary: dict[str, Any] | None, unknown_reason: str | None) -> dict[str, Any]:
        payload = deepcopy(current)
        payload["lifecycle"] = outcome
        if external_ref is not None:
            payload["external_ref"] = external_ref
        if failure_summary is not None:
            payload["failure_summary"] = failure_summary
        if unknown_reason is not None:
            payload["unknown_reason"] = unknown_reason
        return payload

    def _proposal_operation(self, *, operation_id: str, operation: str, proposal_id: str, owner_ref: str, space_id: str, created_by: str, typed_payload: dict[str, Any], schema: str, expected_version: int | None = None) -> CommitOperation:
        self._validate(typed_payload, schema, "shadow.action.operation-invalid")
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=proposal_id, record_type=PROPOSAL_RECORD_TYPE, target_schema_ref=schema, owner_ref=owner_ref, space_id=space_id, created_by=created_by, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.action-proposal", origin_ref=proposal_id), retention_policy_ref=RETENTION_REF, typed_payload=typed_payload, expected_version=expected_version)

    def _action_operation(self, *, operation_id: str, action_id: str, owner_ref: str, space_id: str, created_by: str, typed_payload: dict[str, Any], expected_version: int | None, origin_ref: str, operation: str = "update") -> CommitOperation:
        self._validate(typed_payload, ACTION_PAYLOAD_SCHEMA, "shadow.action.operation-invalid")
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=action_id, record_type=ACTION_RECORD_TYPE, target_schema_ref=ACTION_PAYLOAD_SCHEMA, owner_ref=owner_ref, space_id=space_id, created_by=created_by, data_classification=typed_payload["data_classification"], provenance=Provenance(origin_type="shadow.origin.action", origin_ref=origin_ref), retention_policy_ref=RETENTION_REF, typed_payload=typed_payload, expected_version=expected_version)

    def _commit(self, operations: list[CommitOperation], *, owner_ref: str, space_id: str, idempotency_key: str, request_digest: str, commit_request_id: str, actor_ref: str) -> Any:
        result = self.authority.commit(CommitPlan(commit_request_id=commit_request_id, idempotency_scope=f"action:{owner_ref}:{space_id}", idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=actor_ref, operations=operations, prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Action expected version does not match the current head.", category="conflict")
        if result.outcome == "failed":
            details = result.structured_error or {}
            raise _error(details.get("code", "shadow.action.commit-failed"), details.get("message", "Action commit failed."), details, category=details.get("category", "validation"))
        return result

    def _prior(self, principal_ref: str, space_id: str, idempotency_key: str, request_digest: str) -> dict[str, Any] | None:
        prior = self.repository.idempotency_result(f"action:{principal_ref}:{space_id}", idempotency_key)
        if prior is not None and prior["request_digest"] != request_digest:
            raise _error("shadow.repository.idempotency-mismatch", "Action idempotency key was reused with a different request digest.", category="conflict")
        return prior

    def _record_from_result(self, result: Any, record_id: str) -> dict[str, Any]:
        operation_result = next(item for item in result.operation_results if item.record_id == record_id)
        return self._record_from_operation(operation_result)

    def _record_from_operation(self, operation_result: Any | None) -> dict[str, Any] | None:
        if operation_result is None or operation_result.resulting_version is None:
            return None
        record = self.repository.get(operation_result.record_id, operation_result.resulting_version)
        if record is None:
            raise _error("shadow.repository.record-missing", "Action record could not be read back.")
        return record

    @staticmethod
    def _assert_boundary(record: dict[str, Any], principal_ref: str, space_id: str) -> None:
        if record["owner_ref"] != principal_ref or record["space_id"] != space_id:
            raise _error("shadow.action.unauthorized", "Action owner or space does not match the request.", {"record_id": record["record_id"]}, category="unauthorized")

    def _validate(self, payload: dict[str, Any], schema: str, code: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error(code, "Action payload does not satisfy the Action Profile contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc

    def _require_available(self) -> None:
        if not self.repository.available:
            raise _error("shadow.repository.unavailable", "Canonical Repository is unavailable; Action was not committed.", category="unavailable")


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))


def _invalid(message: str) -> ShadowDomainError:
    return _error("shadow.action.operation-invalid", message)
