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

STATE_SCHEMA = "https://schemas.openshadow.dev/contracts/state/1.0.0"
STATE_PAYLOAD_SCHEMA = f"{STATE_SCHEMA}#/$defs/StatePayload"
STATE_PROPOSAL_SCHEMA = f"{STATE_SCHEMA}#/$defs/StateProposalPayload"
STATE_PROPOSAL_RECORD_SCHEMA = f"{STATE_SCHEMA}#/$defs/StateProposalRecordPayload"
STATE_RECORD_TYPE = "shadow.profile.state"
PROPOSAL_RECORD_TYPE = "shadow.proposal"
RETENTION_REF = StableRecordRef(record_id="retention-default")


class StateSourceAdapter(Protocol):
    def observe(self, *, state_key: str, owner_ref: str, space_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class StateProposalCandidate:
    proposal_id: str
    submitted_by: str
    owner_ref: str
    space_id: str
    payload: dict[str, Any]


class StateService:
    """Proposal/Commit and read boundary for the Phase 3 State Profile."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def propose(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        operation: str,
        state_key: str,
        value_schema_ref: str,
        proposed_value: Any,
        evidence_refs: list[dict[str, Any]],
        source_refs: list[str],
        observed_at: str,
        expires_at: str,
        source_status: str,
        target_state_id: str | None = None,
        expected_version: int | None = None,
        proposal_reason: str | None = None,
    ) -> StateProposalCandidate:
        if operation not in {"create", "update", "logical_delete"}:
            raise _invalid("Unsupported State proposal operation.", {"operation": operation})
        if operation == "create" and (target_state_id is not None or expected_version is not None):
            raise _invalid("State create cannot include a target or expected version.")
        if operation != "create" and (not target_state_id or expected_version is None):
            raise _invalid("State update and logical delete require target and expected version.")
        if operation != "create":
            self._load_target(
                target_state_id or "",
                owner_ref=owner_ref,
                space_id=space_id,
                require_active=True,
                expected_version=expected_version,
            )
        proposal = {
            "proposed_operation": operation,
            "targets": (
                []
                if operation == "create"
                else [{"state_ref": target_state_id, "expected_version": expected_version}]
            ),
            "state_key": state_key,
            "value_schema_ref": value_schema_ref,
            "proposed_value": proposed_value,
            "evidence_refs": evidence_refs,
            "source_refs": source_refs,
            "observed_at": observed_at,
            "expires_at": expires_at,
            "source_status": source_status,
        }
        if proposal_reason:
            proposal["proposal_reason"] = proposal_reason
        self._validate(proposal, STATE_PROPOSAL_SCHEMA, "shadow.state.operation-invalid")
        proposal_id = f"proposal-{sha256_digest({'owner': owner_ref, 'space': space_id, 'proposal': proposal})[7:39]}"
        return StateProposalCandidate(
            proposal_id=proposal_id,
            submitted_by=submitted_by,
            owner_ref=owner_ref,
            space_id=space_id,
            payload=proposal,
        )

    def submit_proposal(
        self, candidate: StateProposalCandidate, *, idempotency_key: str
    ) -> dict[str, Any]:
        self._require_available()
        record_payload = {
            "proposal_type": "shadow.state-proposal",
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
            typed_payload=record_payload,
        )
        result = self._commit(
            operations=[operation],
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
            raise _error(
                "shadow.state.not-found", "State Proposal was not found.", {"record_id": proposal_id}
            )
        self._assert_boundary(proposal_record, principal_ref, space_id)
        if proposal_record["record_type"] != PROPOSAL_RECORD_TYPE:
            raise _invalid("Target record is not a State Proposal.")
        record_payload = proposal_record["typed_payload"]
        request_digest = sha256_digest(
            {
                "proposal_id": proposal_id,
                "proposal": record_payload.get("proposal"),
                "expected": proposal_expected_version,
            }
        )
        prior = self.repository.idempotency_result(
            f"state:{principal_ref}:{space_id}", idempotency_key
        )
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise _error(
                    "shadow.repository.idempotency-mismatch",
                    "State idempotency key was reused with a different request digest.",
                )
            prior_result = prior["result"]
            state_result = next(
                (item for item in prior_result.operation_results if item.record_id != proposal_id),
                None,
            )
            if state_result and state_result.resulting_version:
                state_record = self.get_state(
                    state_result.record_id, principal_ref=principal_ref, space_id=space_id
                )
                return {
                    "decision": "accepted",
                    "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
                    "state_ref": {
                        "record_id": state_result.record_id,
                        "version": state_result.resulting_version,
                    },
                    "replayed": True,
                    "record": state_record,
                }
        if record_payload.get("status") != "pending":
            raise _error(
                "shadow.state.head-not-active",
                "State Proposal is no longer pending.",
                {"record_id": proposal_id, "status": record_payload.get("status")},
            )
        proposal = record_payload["proposal"]
        target = proposal["targets"][0] if proposal["targets"] else None
        state_id = (
            target["state_ref"]
            if target
            else f"state-{sha256_digest({'owner': principal_ref, 'space': space_id, 'state_key': proposal['state_key']})[7:39]}"
        )
        current_state = None
        if target:
            current_state = self._load_target(
                state_id,
                owner_ref=principal_ref,
                space_id=space_id,
                require_active=True,
                expected_version=target["expected_version"],
            )
        elif self.repository.get(state_id) is not None:
            raise _error(
                "shadow.repository.expected-version-conflict",
                "A State already exists for this state key.",
                {"record_id": state_id},
            )
        now = datetime.now(UTC)
        payload = {
            "state_key": proposal["state_key"],
            "value_schema_ref": proposal["value_schema_ref"],
            "typed_value": (
                current_state["typed_payload"].get("typed_value")
                if proposal["proposed_operation"] == "logical_delete" and current_state
                else proposal["proposed_value"]
            ),
            "evidence_refs": proposal["evidence_refs"],
            "source_refs": proposal["source_refs"],
            "observed_at": proposal["observed_at"],
            "expires_at": proposal["expires_at"],
            "source_status": proposal["source_status"],
            "freshness": self.compute_freshness(proposal, now=now),
        }
        state_operation = self._state_operation(
            operation_id=f"operation-{state_id}-{proposal['proposed_operation']}",
            operation="create" if not target else "update",
            state_id=state_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=payload,
            expected_version=target["expected_version"] if target else None,
            record_state=(
                "logically_deleted"
                if proposal["proposed_operation"] == "logical_delete"
                else "active"
            ),
            origin_ref=proposal_id,
        )
        accepted_payload = deepcopy(record_payload)
        accepted_payload["status"] = "accepted"
        accepted_payload["resulting_state_ref"] = state_id
        proposal_operation = self._proposal_operation(
            operation_id=f"operation-{proposal_id}-accept",
            operation="update",
            proposal_id=proposal_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=accepted_payload,
            expected_version=proposal_expected_version,
        )
        result = self._commit(
            operations=[proposal_operation, state_operation],
            owner_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            commit_request_id=f"commit-request-{proposal_id}-accept",
            actor_ref=principal_ref,
        )
        state_result = next(item for item in result.operation_results if item.record_id == state_id)
        resulting_version = state_result.resulting_version
        if resulting_version is None:
            raise _error("shadow.repository.record-missing", "Accepted State has no resulting version.")
        return {
            "decision": "accepted",
            "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
            "state_ref": {"record_id": state_id, "version": resulting_version},
            "replayed": result.outcome == "idempotent_replay",
            "record": self.get_state(state_id, principal_ref=principal_ref, space_id=space_id),
        }

    def list_states(
        self, *, owner_ref: str | None, space_id: str, state_key: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        records = self.repository.query_heads(
            owner_refs={owner_ref} if owner_ref else None,
            space_ids={space_id},
            record_types={STATE_RECORD_TYPE},
            record_states={"active", "logically_deleted", "erased"},
            limit=None,
        )
        result = []
        for record in sorted(records, key=lambda item: item["record_id"]):
            if record["record_state"] != "active":
                continue
            if state_key and record["typed_payload"].get("state_key") != state_key:
                continue
            result.append(self._with_freshness(record))
        return result[:limit]

    def get_state(
        self, state_id: str, *, principal_ref: str | None = None, space_id: str | None = None, enforce_owner: bool = True
    ) -> dict[str, Any] | None:
        record = self.repository.get(state_id)
        if record is None or record["record_type"] != STATE_RECORD_TYPE:
            return None
        if principal_ref is not None and space_id is not None and enforce_owner:
            self._assert_boundary(record, principal_ref, space_id)
        elif space_id is not None and record["space_id"] != space_id:
            raise _error("shadow.state.space-mismatch", "State does not belong to the requested Space.", category="unauthorized")
        return self._with_freshness(record)

    @staticmethod
    def compute_freshness(payload: dict[str, Any], *, now: datetime | None = None) -> str:
        now = now or datetime.now(UTC)
        if payload.get("source_status") != "available":
            return "stale" if payload.get("typed_value") is not None else "unknown"
        try:
            expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            return "unknown"
        if expires_at <= now:
            return "stale" if payload.get("typed_value") is not None else "unknown"
        return "fresh"

    def _with_freshness(self, record: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(record)
        result["typed_payload"]["freshness"] = self.compute_freshness(result["typed_payload"])
        return result

    def _load_target(
        self,
        state_id: str,
        *,
        owner_ref: str,
        space_id: str,
        require_active: bool,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        head = self.repository.get(state_id)
        record = self.repository.get(state_id, expected_version) if expected_version else head
        if head is None or record is None or head["record_type"] != STATE_RECORD_TYPE:
            raise _error("shadow.state.not-found", "State was not found.", {"record_id": state_id})
        self._assert_boundary(head, owner_ref, space_id)
        self._assert_boundary(record, owner_ref, space_id)
        if require_active and head["record_state"] != "active":
            raise _error(
                "shadow.state.head-not-active",
                "State head is not active.",
                {"record_id": state_id, "record_state": head["record_state"]},
                category="conflict",
            )
        if expected_version is not None and head["version"] != expected_version:
            raise _error(
                "shadow.repository.expected-version-conflict",
                "State expected version does not match the current head.",
                {"record_id": state_id, "expected_version": expected_version, "current_version": head["version"]},
                category="conflict",
            )
        if require_active and record["record_state"] != "active":
            raise _error(
                "shadow.state.head-not-active",
                "State head is not active.",
                {"record_id": state_id, "record_state": record["record_state"]},
            )
        return record

    @staticmethod
    def _heads(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        heads: dict[str, dict[str, Any]] = {}
        for record in records:
            prior = heads.get(record["record_id"])
            if prior is None or record["version"] > prior["version"]:
                heads[record["record_id"]] = record
        return heads

    @staticmethod
    def _assert_boundary(record: dict[str, Any], principal_ref: str, space_id: str) -> None:
        if record["owner_ref"] != principal_ref or record["space_id"] != space_id:
            raise _error(
                "shadow.state.owner-space-mismatch",
                "State owner or space does not match the request.",
                {"record_id": record["record_id"]},
            )

    def _validate(self, payload: dict[str, Any], schema: str, code: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error(
                code,
                "State payload does not satisfy the State Profile contract.",
                {"path": list(exc.absolute_path), "detail": exc.message},
            ) from exc

    def _proposal_operation(
        self,
        *,
        operation_id: str,
        operation: str,
        proposal_id: str,
        owner_ref: str,
        space_id: str,
        created_by: str,
        typed_payload: dict[str, Any],
        expected_version: int | None = None,
    ) -> CommitOperation:
        self._validate(typed_payload, STATE_PROPOSAL_RECORD_SCHEMA, "shadow.state.operation-invalid")
        return CommitOperation(
            operation_id=operation_id,
            operation=operation,
            record_id=proposal_id,
            record_type=PROPOSAL_RECORD_TYPE,
            target_schema_ref=STATE_PROPOSAL_RECORD_SCHEMA,
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=created_by,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.state-proposal", origin_ref=proposal_id),
            retention_policy_ref=RETENTION_REF,
            typed_payload=typed_payload,
            expected_version=expected_version,
        )

    def _state_operation(
        self,
        *,
        operation_id: str,
        operation: str,
        state_id: str,
        owner_ref: str,
        space_id: str,
        created_by: str,
        typed_payload: dict[str, Any],
        expected_version: int | None,
        record_state: str,
        origin_ref: str,
    ) -> CommitOperation:
        self._validate(typed_payload, STATE_PAYLOAD_SCHEMA, "shadow.state.operation-invalid")
        return CommitOperation(
            operation_id=operation_id,
            operation=operation,
            record_id=state_id,
            record_type=STATE_RECORD_TYPE,
            target_schema_ref=STATE_PAYLOAD_SCHEMA,
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=created_by,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.state-proposal", origin_ref=origin_ref),
            retention_policy_ref=RETENTION_REF,
            record_state=record_state,
            typed_payload=typed_payload,
            expected_version=expected_version,
        )

    def _commit(
        self,
        *,
        operations: list[CommitOperation],
        owner_ref: str,
        space_id: str,
        idempotency_key: str,
        request_digest: str,
        commit_request_id: str,
        actor_ref: str,
    ) -> Any:
        result = self.authority.commit(
            CommitPlan(
                commit_request_id=commit_request_id,
                idempotency_scope=f"state:{owner_ref}:{space_id}",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                actor_ref=actor_ref,
                operations=operations,
                prepared_at=utc_timestamp(),
            )
        )
        if result.outcome == "conflict":
            raise _error(
                "shadow.repository.expected-version-conflict",
                "State expected version does not match the current head.",
                result.model_dump(mode="json", exclude_none=True),
            )
        if result.outcome == "failed":
            details = result.structured_error or {}
            raise _error(
                details.get("code", "shadow.state.commit-failed"),
                details.get("message", "State commit failed."),
                details,
                category=details.get("category", "validation"),
            )
        return result

    def _record_from_result(self, result: Any, record_id: str) -> dict[str, Any]:
        operation_result = next(item for item in result.operation_results if item.record_id == record_id)
        version = operation_result.resulting_version
        record = self.repository.get(record_id, version)
        if record is None:
            raise _error("shadow.repository.record-missing", "Committed State record could not be read back.")
        return record

    def _require_available(self) -> None:
        if not self.repository.available:
            raise _error(
                "shadow.repository.unavailable",
                "Canonical Repository is unavailable; State was not committed.",
                category="unavailable",
            )


def _error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    *,
    category: str = "validation",
) -> ShadowDomainError:
    return ShadowDomainError(
        ShadowError(code=code, category=category, message=message, typed_details=details)
    )


def _invalid(message: str, details: dict[str, Any] | None = None) -> ShadowDomainError:
    return _error("shadow.state.operation-invalid", message, details)
