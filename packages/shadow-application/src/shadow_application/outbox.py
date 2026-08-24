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

OUTBOX_SCHEMA = "https://schemas.openshadow.dev/contracts/outbox/1.0.0"
INTENT_SCHEMA = f"{OUTBOX_SCHEMA}#/$defs/OutboxIntentPayload"
DELIVERY_RESULT_SCHEMA = f"{OUTBOX_SCHEMA}#/$defs/DeliveryResultPayload"
RECONCILIATION_SCHEMA = f"{OUTBOX_SCHEMA}#/$defs/ReconciliationPayload"
INTENT_RECORD_TYPE = "shadow.profile.outbox-intent"
DELIVERY_RESULT_RECORD_TYPE = "shadow.outbox.delivery-result"
RECONCILIATION_RECORD_TYPE = "shadow.outbox.reconciliation"
ACTION_RECORD_TYPE = "shadow.profile.action"
RETENTION_REF = StableRecordRef(record_id="retention-default")
SUPPORTED_DELIVERY_CLASSES = {"reliable-side-effect", "emergency"}


class OutboxDeliveryAdapter(Protocol):
    def deliver(self, intent: dict[str, Any]) -> dict[str, Any]: ...

    def reconcile(self, intent: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OutboxIntentCandidate:
    intent_id: str
    principal_ref: str
    space_id: str
    payload: dict[str, Any]


class OutboxService:
    """Canonical boundary for reliable side effects; it is not a queue implementation."""

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
        self.supported_capabilities = supported_capabilities or {
            "shadow.action.notify",
            "shadow.action.lookup",
        }

    def propose_intent(
        self,
        *,
        principal_ref: str,
        space_id: str,
        action_ref: dict[str, Any],
        target_ref: dict[str, Any],
        operation_kind: str,
        capability: str,
        delivery_class: str,
        parameter_digest: str,
        data_classification: str,
        side_effect_level: str,
        deadline: str,
        idempotency_key: str,
    ) -> OutboxIntentCandidate:
        self._require_available()
        if capability not in self.supported_capabilities:
            raise _error(
                "shadow.outbox.capability-unsupported",
                "Outbox capability is not allowlisted.",
                {"capability": capability},
                category="incompatible",
            )
        action = self.repository.get(action_ref.get("record_id", ""))
        if action is None or action.get("record_type") != ACTION_RECORD_TYPE:
            raise _error("shadow.outbox.not-found", "Referenced Action was not found.")
        self._assert_boundary(action, principal_ref, space_id)
        if action.get("record_state") != "active":
            raise _error(
                "shadow.outbox.invalid-transition",
                "An inactive Action cannot create an Outbox Intent.",
                category="conflict",
            )
        if action_ref.get("version") != action.get("version"):
            raise _error(
                "shadow.repository.expected-version-conflict",
                "Action reference version does not match its current head.",
                {"expected_version": action_ref.get("version"), "current_version": action.get("version")},
                category="conflict",
            )
        self._check_deadline(deadline)
        payload = {
            "action_ref": action_ref,
            "target_ref": target_ref,
            "operation_kind": operation_kind,
            "capability": capability,
            "delivery_class": delivery_class,
            "parameter_digest": parameter_digest,
            "data_classification": data_classification,
            "side_effect_level": side_effect_level,
            "deadline": deadline,
            "idempotency_key": idempotency_key,
            "lifecycle": "pending",
            "created_at": utc_timestamp(),
            "attempt_count": 0,
        }
        self._validate(payload, INTENT_SCHEMA)
        intent_id = f"outbox-{sha256_digest({'owner': principal_ref, 'space': space_id, 'payload': payload})[7:39]}"
        return OutboxIntentCandidate(intent_id, principal_ref, space_id, payload)

    def create_intent(self, candidate: OutboxIntentCandidate) -> dict[str, Any]:
        self._require_available()
        request_digest = sha256_digest(candidate.payload)
        prior = self._prior(candidate.principal_ref, candidate.space_id, candidate.payload["idempotency_key"], request_digest)
        if prior is not None:
            return {"record": self._record_from_result(prior["result"], candidate.intent_id), "replayed": True}
        operation = self._intent_operation(
            operation_id=f"operation-{candidate.intent_id}-create",
            intent_id=candidate.intent_id,
            operation="create",
            owner_ref=candidate.principal_ref,
            space_id=candidate.space_id,
            created_by=candidate.principal_ref,
            payload=candidate.payload,
            origin_ref=candidate.payload["action_ref"]["record_id"],
        )
        result = self._commit(
            [operation],
            owner_ref=candidate.principal_ref,
            space_id=candidate.space_id,
            idempotency_key=candidate.payload["idempotency_key"],
            request_digest=request_digest,
            actor_ref=candidate.principal_ref,
            commit_request_id=f"commit-request-{candidate.intent_id}-create",
        )
        return {"record": self._record_from_result(result, candidate.intent_id), "replayed": result.outcome == "idempotent_replay"}

    def lease_intent(
        self,
        *,
        intent_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        lease_owner: str,
        lease_expires_at: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        intent = self._load_intent(intent_id, principal_ref, space_id, expected_version)
        now = datetime.now(UTC)
        current_state = intent["typed_payload"]["lifecycle"]
        if current_state == "leased":
            current_expiry = datetime.fromisoformat(intent["typed_payload"]["lease"]["expires_at"].replace("Z", "+00:00"))
            if current_expiry > now:
                raise _error("shadow.outbox.invalid-transition", "Outbox Intent already has an active lease.", category="conflict")
        elif current_state != "pending":
            raise _error("shadow.outbox.invalid-transition", "Only pending or expired leased Intents can be leased.", category="conflict")
        self._check_deadline(lease_expires_at)
        payload = deepcopy(intent["typed_payload"])
        payload["lifecycle"] = "leased"
        payload["lease"] = {"lease_owner": lease_owner, "expires_at": lease_expires_at}
        payload["attempt_count"] += 1
        request_digest = sha256_digest({"intent": intent_id, "expected_version": expected_version, "lease": payload["lease"]})
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            return {"record": self._record_from_result(prior["result"], intent_id), "replayed": True}
        operation = self._intent_operation(
            operation_id=f"operation-{intent_id}-lease",
            intent_id=intent_id,
            operation="update",
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            payload=payload,
            expected_version=expected_version,
            origin_ref=intent_id,
        )
        result = self._commit([operation], owner_ref=principal_ref, space_id=space_id, idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=principal_ref, commit_request_id=f"commit-request-{intent_id}-lease")
        return {"record": self._record_from_result(result, intent_id), "replayed": result.outcome == "idempotent_replay"}

    def record_delivery_result(
        self,
        *,
        intent_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        result_payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        self._validate(result_payload, DELIVERY_RESULT_SCHEMA)
        request_digest = sha256_digest({"intent": intent_id, "expected_version": expected_version, "result": result_payload})
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            result_id = f"outbox-result-{sha256_digest({'intent': intent_id, 'payload': result_payload})[7:39]}"
            return {"result": self._record_from_result(prior["result"], result_id), "record": self._record_from_result(prior["result"], intent_id), "replayed": True}
        intent = self._load_intent(intent_id, principal_ref, space_id, expected_version)
        if intent["typed_payload"]["lifecycle"] != "leased":
            raise _error("shadow.outbox.invalid-transition", "Delivery results require a leased Intent.", category="conflict")
        outcome = result_payload["outcome"]
        payload = deepcopy(intent["typed_payload"])
        payload["lifecycle"] = outcome
        payload.pop("lease", None)
        if result_payload.get("provider_ref") is not None:
            payload["provider_ref"] = result_payload["provider_ref"]
        if outcome == "failed" and result_payload.get("reason"):
            payload["failure_summary"] = {"reason": result_payload["reason"]}
        if outcome == "unknown":
            payload["unknown_reason"] = result_payload.get("reason", "Provider outcome was not confirmed.")
        result_id = f"outbox-result-{sha256_digest({'intent': intent_id, 'payload': result_payload})[7:39]}"
        result_operation = self._result_operation(result_id, DELIVERY_RESULT_RECORD_TYPE, DELIVERY_RESULT_SCHEMA, principal_ref, space_id, result_payload, intent_id)
        intent_operation = self._intent_operation(operation_id=f"operation-{intent_id}-result", intent_id=intent_id, operation="update", owner_ref=principal_ref, space_id=space_id, created_by=principal_ref, payload=payload, expected_version=expected_version, origin_ref=result_id)
        commit = self._commit([result_operation, intent_operation], owner_ref=principal_ref, space_id=space_id, idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=principal_ref, commit_request_id=f"commit-request-{result_id}")
        return {"result": self._record_from_result(commit, result_id), "record": self._record_from_result(commit, intent_id), "replayed": commit.outcome == "idempotent_replay"}

    def reconcile_unknown(
        self,
        *,
        intent_id: str,
        expected_version: int,
        principal_ref: str,
        space_id: str,
        reconciliation_payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        self._validate(reconciliation_payload, RECONCILIATION_SCHEMA)
        request_digest = sha256_digest({"intent": intent_id, "expected_version": expected_version, "reconciliation": reconciliation_payload})
        prior = self._prior(principal_ref, space_id, idempotency_key, request_digest)
        recon_id = f"outbox-reconciliation-{sha256_digest({'intent': intent_id, 'payload': reconciliation_payload})[7:39]}"
        if prior is not None:
            return {"reconciliation": self._record_from_result(prior["result"], recon_id), "record": self._record_from_result(prior["result"], intent_id), "replayed": True}
        intent = self._load_intent(intent_id, principal_ref, space_id, expected_version)
        if intent["typed_payload"]["lifecycle"] != "unknown":
            raise _error("shadow.outbox.invalid-transition", "Only unknown Intents can be reconciled.", category="conflict")
        payload = deepcopy(intent["typed_payload"])
        payload["lifecycle"] = reconciliation_payload["outcome"]
        payload["provider_ref"] = reconciliation_payload["provider_ref"]
        payload.setdefault("reconciliation_refs", []).append({"record_id": recon_id, "version": 1})
        recon_operation = self._result_operation(recon_id, RECONCILIATION_RECORD_TYPE, RECONCILIATION_SCHEMA, principal_ref, space_id, reconciliation_payload, intent_id)
        intent_operation = self._intent_operation(operation_id=f"operation-{intent_id}-reconcile", intent_id=intent_id, operation="update", owner_ref=principal_ref, space_id=space_id, created_by=principal_ref, payload=payload, expected_version=expected_version, origin_ref=recon_id)
        commit = self._commit([recon_operation, intent_operation], owner_ref=principal_ref, space_id=space_id, idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=principal_ref, commit_request_id=f"commit-request-{recon_id}")
        return {"reconciliation": self._record_from_result(commit, recon_id), "record": self._record_from_result(commit, intent_id), "replayed": commit.outcome == "idempotent_replay"}

    def get_intent(self, intent_id: str, principal_ref: str | None = None, space_id: str | None = None) -> dict[str, Any] | None:
        record = self.repository.get(intent_id)
        if record is None or record.get("record_type") != INTENT_RECORD_TYPE:
            return None
        if principal_ref is not None and space_id is not None:
            self._assert_boundary(record, principal_ref, space_id)
        return record

    def list_intents(self, *, principal_ref: str, space_id: str, limit: int = 50) -> list[dict[str, Any]]:
        records = self.repository.query_heads(
            owner_refs={principal_ref},
            space_ids={space_id},
            record_types={INTENT_RECORD_TYPE},
            record_states={"active"},
            limit=None,
        )
        return sorted(records, key=lambda item: item["record_id"])[:limit]

    def _load_intent(self, intent_id: str, principal_ref: str, space_id: str, expected_version: int) -> dict[str, Any]:
        record = self.get_intent(intent_id)
        if record is None:
            raise _error("shadow.outbox.not-found", "Outbox Intent was not found.")
        self._assert_boundary(record, principal_ref, space_id)
        if record["record_state"] != "active":
            raise _error("shadow.outbox.invalid-transition", "Outbox Intent head is not active.", category="conflict")
        if record["version"] != expected_version:
            raise _error("shadow.repository.expected-version-conflict", "Outbox Intent version does not match current head.", {"expected_version": expected_version, "current_version": record["version"]}, category="conflict")
        return record

    def _intent_operation(self, *, operation_id: str, intent_id: str, operation: str, owner_ref: str, space_id: str, created_by: str, payload: dict[str, Any], origin_ref: str, expected_version: int | None = None) -> CommitOperation:
        self._validate(payload, INTENT_SCHEMA)
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=intent_id, record_type=INTENT_RECORD_TYPE, target_schema_ref=INTENT_SCHEMA, owner_ref=owner_ref, space_id=space_id, created_by=created_by, data_classification=payload["data_classification"], provenance=Provenance(origin_type="shadow.origin.outbox", origin_ref=origin_ref), retention_policy_ref=RETENTION_REF, typed_payload=payload, expected_version=expected_version)

    def _result_operation(self, record_id: str, record_type: str, schema: str, owner_ref: str, space_id: str, payload: dict[str, Any], origin_ref: str) -> CommitOperation:
        self._validate(payload, schema)
        return CommitOperation(operation_id=f"operation-{record_id}-create", operation="create", record_id=record_id, record_type=record_type, target_schema_ref=schema, owner_ref=owner_ref, space_id=space_id, created_by=owner_ref, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.outbox", origin_ref=origin_ref), retention_policy_ref=RETENTION_REF, typed_payload=payload)

    def _commit(self, operations: list[CommitOperation], *, owner_ref: str, space_id: str, idempotency_key: str, request_digest: str, actor_ref: str, commit_request_id: str) -> Any:
        result = self.authority.commit(CommitPlan(commit_request_id=commit_request_id, idempotency_scope=f"outbox:{owner_ref}:{space_id}", idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=actor_ref, operations=operations, prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Outbox expected version does not match current head.", category="conflict")
        if result.outcome == "failed":
            details = result.structured_error or {}
            raise _error(details.get("code", "shadow.outbox.commit-failed"), details.get("message", "Outbox commit failed."), details, category=details.get("category", "validation"))
        return result

    def _prior(self, principal_ref: str, space_id: str, key: str, digest: str) -> dict[str, Any] | None:
        prior = self.repository.idempotency_result(f"outbox:{principal_ref}:{space_id}", key)
        if prior is not None and prior["request_digest"] != digest:
            raise _error("shadow.repository.idempotency-mismatch", "Outbox idempotency key was reused with a different request digest.", category="conflict")
        return prior

    def _record_from_result(self, result: Any, record_id: str) -> dict[str, Any] | None:
        operation_result = next((item for item in result.operation_results if item.record_id == record_id), None)
        if operation_result is None or operation_result.resulting_version is None:
            return None
        record = self.repository.get(record_id, operation_result.resulting_version)
        if record is None:
            raise _error("shadow.repository.record-missing", "Outbox record could not be read back.")
        return record

    def _validate(self, payload: dict[str, Any], schema: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error("shadow.outbox.operation-invalid", "Outbox payload does not satisfy its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc

    @staticmethod
    def _assert_boundary(record: dict[str, Any], principal_ref: str, space_id: str) -> None:
        if record["owner_ref"] != principal_ref or record["space_id"] != space_id:
            raise _error("shadow.outbox.unauthorized", "Outbox owner or space does not match the request.", category="unauthorized")

    @staticmethod
    def _check_deadline(value: str) -> None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise _error("shadow.outbox.invalid-transition", "Outbox deadline is invalid.") from exc
        if parsed <= datetime.now(UTC):
            raise _error("shadow.outbox.invalid-transition", "Outbox deadline has expired.", category="conflict")

    def _require_available(self) -> None:
        if not self.repository.available:
            raise _error("shadow.repository.unavailable", "Canonical Repository is unavailable; Outbox was not committed.", category="unavailable")


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))
