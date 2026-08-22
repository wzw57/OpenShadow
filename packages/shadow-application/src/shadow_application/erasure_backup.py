from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

ERASURE_SCHEMA = "https://schemas.openshadow.dev/contracts/erasure/1.0.0"
ERASURE_REQUEST_SCHEMA = f"{ERASURE_SCHEMA}#/$defs/ErasureRequest"
BACKUP_METADATA_SCHEMA = f"{ERASURE_SCHEMA}#/$defs/BackupMetadata"
ERASURE_RECORD_TYPE = "shadow.erasure.request"
BACKUP_RECORD_TYPE = "shadow.backup.metadata"
RETENTION_REF = StableRecordRef(record_id="retention-default")


class CrossComponentErasureAdapter(Protocol):
    def quiesce(self, request: dict[str, Any], component_ref: str) -> list[str]: ...

    def erase(self, request: dict[str, Any], component_ref: str) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class ErasureRequestCandidate:
    request_id: str
    owner_ref: str
    space_id: str
    payload: dict[str, Any]


class ErasureService:
    """Canonical state machine for cross-component erasure intent and evidence."""

    def __init__(self, repository: CanonicalRepository, authority: CommitAuthority, registry: ContractRegistry) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def propose_request(
        self,
        *,
        owner_ref: str,
        space_id: str,
        scope_ref: str,
        target_refs: list[str],
        policy_ref: dict[str, Any],
        idempotency_key: str,
        component_statuses: list[dict[str, Any]],
    ) -> ErasureRequestCandidate:
        self._require_available()
        if not target_refs or len(target_refs) != len(set(target_refs)):
            raise _error("shadow.erasure.scope-invalid", "Erasure scope must contain unique targets.")
        if not component_statuses or len({item.get("component_ref") for item in component_statuses}) != len(component_statuses):
            raise _error("shadow.erasure.scope-invalid", "Erasure component set must be non-empty and unique.")
        payload = {
            "request_id": "pending",
            "owner_ref": owner_ref,
            "space_id": space_id,
            "scope_ref": scope_ref,
            "target_refs": target_refs,
            "policy_ref": policy_ref,
            "requested_at": utc_timestamp(),
            "idempotency_key": idempotency_key,
            "lifecycle": "pending",
            "component_statuses": component_statuses,
        }
        request_id = f"erasure-request-{sha256_digest({'owner': owner_ref, 'space': space_id, 'scope': scope_ref, 'targets': target_refs, 'key': idempotency_key})[7:39]}"
        payload["request_id"] = request_id
        self._validate(payload, ERASURE_REQUEST_SCHEMA)
        return ErasureRequestCandidate(request_id, owner_ref, space_id, payload)

    def create_request(self, candidate: ErasureRequestCandidate) -> dict[str, Any]:
        self._require_available()
        digest = sha256_digest(candidate.payload)
        prior = self._prior(candidate.owner_ref, candidate.space_id, candidate.payload["idempotency_key"], digest)
        if prior is not None:
            return {"record": self._record_from_result(prior["result"], candidate.request_id), "replayed": True}
        operation = self._operation(
            operation_id=f"operation-{candidate.request_id}-create",
            record_id=candidate.request_id,
            record_type=ERASURE_RECORD_TYPE,
            schema=ERASURE_REQUEST_SCHEMA,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            payload=candidate.payload,
            origin_ref=candidate.request_id,
            operation="create",
        )
        result = self._commit([operation], owner_ref=candidate.owner_ref, space_id=candidate.space_id, key=candidate.payload["idempotency_key"], digest=digest, request_id=f"commit-request-{candidate.request_id}-create")
        return {"record": self._record_from_result(result, candidate.request_id), "replayed": result.outcome == "idempotent_replay"}

    def update_component_status(
        self,
        *,
        request_id: str,
        expected_version: int,
        owner_ref: str,
        space_id: str,
        component_ref: str,
        state: str,
        evidence_refs: list[str],
        idempotency_key: str,
        failure_code: str | None = None,
        retention_until: str | None = None,
    ) -> dict[str, Any]:
        self._require_available()
        request_digest = sha256_digest({"request": request_id, "version": expected_version, "component": component_ref, "state": state, "evidence": evidence_refs, "failure": failure_code, "retention": retention_until})
        prior = self._prior(owner_ref, space_id, idempotency_key, request_digest)
        if prior is not None:
            return {"record": self._record_from_result(prior["result"], request_id), "replayed": True}
        record = self._load(request_id, owner_ref, space_id, expected_version)
        payload = deepcopy(record["typed_payload"])
        statuses = payload["component_statuses"]
        target = next((item for item in statuses if item["component_ref"] == component_ref), None)
        if target is None:
            raise _error("shadow.erasure.scope-invalid", "Component is not part of the Erasure scope.")
        if target["state"] == "erased" and state != "erased":
            raise _error("shadow.erasure.partial-failure", "An erased component cannot be resurrected.", category="conflict")
        if state not in {"pending", "quiesced", "erased", "failed", "unreachable", "unknown"}:
            raise _error("shadow.erasure.scope-invalid", "Unknown component state.")
        target.update({"state": state, "updated_at": utc_timestamp(), "evidence_refs": evidence_refs})
        if failure_code is not None:
            target["failure_code"] = failure_code
        if retention_until is not None:
            target["retention_until"] = retention_until
        states = {item["state"] for item in statuses}
        if states == {"erased"}:
            payload["lifecycle"] = "completed"
        elif states & {"failed", "unreachable", "unknown"}:
            payload["lifecycle"] = "partially_completed"
        elif "quiesced" in states:
            payload["lifecycle"] = "dispatching"
        else:
            payload["lifecycle"] = "pending"
        operation = self._operation(operation_id=f"operation-{request_id}-{component_ref}-{state}", record_id=request_id, record_type=ERASURE_RECORD_TYPE, schema=ERASURE_REQUEST_SCHEMA, owner_ref=owner_ref, space_id=space_id, payload=payload, origin_ref=component_ref, expected_version=expected_version)
        result = self._commit([operation], owner_ref=owner_ref, space_id=space_id, key=idempotency_key, digest=request_digest, request_id=f"commit-request-{request_id}-{component_ref}-{state}")
        return {"record": self._record_from_result(result, request_id), "replayed": result.outcome == "idempotent_replay"}

    def dispatch_component(
        self,
        *,
        request_id: str,
        expected_version: int,
        owner_ref: str,
        space_id: str,
        component_ref: str,
        adapter: CrossComponentErasureAdapter,
        idempotency_key: str,
    ) -> dict[str, Any]:
        record = self._load(request_id, owner_ref, space_id, expected_version)
        quiesce_evidence = adapter.quiesce(record, component_ref)
        quiesced = self.update_component_status(request_id=request_id, expected_version=expected_version, owner_ref=owner_ref, space_id=space_id, component_ref=component_ref, state="quiesced", evidence_refs=quiesce_evidence, idempotency_key=f"{idempotency_key}:quiesce")
        erased_evidence = adapter.erase(quiesced["record"], component_ref)
        return self.update_component_status(request_id=request_id, expected_version=quiesced["record"]["version"], owner_ref=owner_ref, space_id=space_id, component_ref=component_ref, state="erased", evidence_refs=erased_evidence, idempotency_key=f"{idempotency_key}:erase")

    def get_request(self, request_id: str, owner_ref: str | None = None, space_id: str | None = None) -> dict[str, Any] | None:
        record = self.repository.get(request_id)
        if record is None or record.get("record_type") != ERASURE_RECORD_TYPE:
            return None
        if owner_ref is not None and space_id is not None:
            self._assert_boundary(record, owner_ref, space_id)
        return record

    def _load(self, request_id: str, owner_ref: str, space_id: str, expected_version: int) -> dict[str, Any]:
        record = self.get_request(request_id)
        if record is None:
            raise _error("shadow.erasure.scope-invalid", "Erasure request was not found.")
        self._assert_boundary(record, owner_ref, space_id)
        if record["record_state"] != "active":
            raise _error("shadow.erasure.already-completed", "Erasure request is not active.", category="conflict")
        if record["version"] != expected_version:
            raise _error("shadow.repository.expected-version-conflict", "Erasure request version does not match current head.", category="conflict")
        if record["typed_payload"]["lifecycle"] == "completed":
            raise _error("shadow.erasure.already-completed", "Erasure request is already completed.", category="conflict")
        return record

    def _operation(self, *, operation_id: str, record_id: str, record_type: str, schema: str, owner_ref: str, space_id: str, payload: dict[str, Any], origin_ref: str, operation: str = "update", expected_version: int | None = None) -> CommitOperation:
        self._validate(payload, schema)
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=record_id, record_type=record_type, target_schema_ref=schema, owner_ref=owner_ref, space_id=space_id, created_by=owner_ref, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.erasure", origin_ref=origin_ref), retention_policy_ref=RETENTION_REF, typed_payload=payload, expected_version=expected_version)

    def _commit(self, operations: list[CommitOperation], *, owner_ref: str, space_id: str, key: str, digest: str, request_id: str) -> Any:
        result = self.authority.commit(CommitPlan(commit_request_id=request_id, idempotency_scope=f"erasure:{owner_ref}:{space_id}", idempotency_key=key, request_digest=digest, actor_ref=owner_ref, operations=operations, prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Erasure expected version does not match current head.", category="conflict")
        if result.outcome == "failed":
            details = result.structured_error or {}
            raise _error(details.get("code", "shadow.erasure.commit-failed"), details.get("message", "Erasure commit failed."), details, category=details.get("category", "validation"))
        return result

    def _prior(self, owner_ref: str, space_id: str, key: str, digest: str) -> dict[str, Any] | None:
        prior = self.repository.idempotency_result(f"erasure:{owner_ref}:{space_id}", key)
        if prior is not None and prior["request_digest"] != digest:
            raise _error("shadow.repository.idempotency-mismatch", "Erasure idempotency key was reused with a different digest.", category="conflict")
        return prior

    def _record_from_result(self, result: Any, record_id: str) -> dict[str, Any] | None:
        operation = next((item for item in result.operation_results if item.record_id == record_id), None)
        if operation is None or operation.resulting_version is None:
            return None
        return self.repository.get(record_id, operation.resulting_version)

    def _validate(self, payload: dict[str, Any], schema: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error("shadow.erasure.scope-invalid", "Erasure payload does not satisfy its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc

    @staticmethod
    def _assert_boundary(record: dict[str, Any], owner_ref: str, space_id: str) -> None:
        if record["owner_ref"] != owner_ref or record["space_id"] != space_id:
            raise _error("shadow.erasure.unauthorized", "Erasure owner or space does not match request.", category="unauthorized")

    def _require_available(self) -> None:
        if not self.repository.available:
            raise _error("shadow.repository.unavailable", "Canonical Repository is unavailable; Erasure was not committed.", category="unavailable")


class BackupMetadataService:
    """Stores only encrypted Portable Export metadata; it never creates backup content."""

    def __init__(self, repository: CanonicalRepository, authority: CommitAuthority, registry: ContractRegistry) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def register(self, *, owner_ref: str, space_id: str, metadata: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        if not self.repository.available:
            raise _error("shadow.repository.unavailable", "Canonical Repository is unavailable; Backup metadata was not committed.", category="unavailable")
        self._validate(metadata)
        if metadata["owner_ref"] != owner_ref or metadata["space_id"] != space_id:
            raise _error("shadow.erasure.unauthorized", "Backup metadata owner or space does not match request.", category="unauthorized")
        record_id = f"backup-metadata-{metadata['backup_id']}"
        digest = sha256_digest(metadata)
        prior = self.repository.idempotency_result(f"backup:{owner_ref}:{space_id}", idempotency_key)
        if prior is not None:
            if prior["request_digest"] != digest:
                raise _error("shadow.repository.idempotency-mismatch", "Backup metadata idempotency key was reused with a different digest.", category="conflict")
            return {"record": self.repository.get(record_id), "replayed": True}
        operation = CommitOperation(operation_id=f"operation-{record_id}-create", operation="create", record_id=record_id, record_type=BACKUP_RECORD_TYPE, target_schema_ref=BACKUP_METADATA_SCHEMA, owner_ref=owner_ref, space_id=space_id, created_by=owner_ref, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.backup-metadata", origin_ref=metadata["backup_id"]), retention_policy_ref=RETENTION_REF, typed_payload=metadata)
        result = self.authority.commit(CommitPlan(commit_request_id=f"commit-request-{record_id}", idempotency_scope=f"backup:{owner_ref}:{space_id}", idempotency_key=idempotency_key, request_digest=digest, actor_ref=owner_ref, operations=[operation], prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Backup metadata already exists.", category="conflict")
        if result.outcome == "failed":
            raise _error("shadow.backup.metadata-invalid", "Backup metadata was not committed.")
        return {"record": self.repository.get(record_id), "replayed": result.outcome == "idempotent_replay"}

    def _validate(self, metadata: dict[str, Any]) -> None:
        try:
            self.registry.validate(metadata, BACKUP_METADATA_SCHEMA)
        except JsonSchemaValidationError as exc:
            code = "shadow.backup.encryption-required" if metadata.get("encrypted") is not True else "shadow.backup.metadata-invalid"
            raise _error(code, "Backup metadata does not satisfy its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))
