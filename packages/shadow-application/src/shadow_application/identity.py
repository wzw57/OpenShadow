from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

IDENTITY_SCHEMA = "https://schemas.openshadow.dev/contracts/identity/1.0.0"
ENDPOINT_PAYLOAD_SCHEMA = f"{IDENTITY_SCHEMA}#/$defs/EndpointPayload"
SPACE_PAYLOAD_SCHEMA = f"{IDENTITY_SCHEMA}#/$defs/SpacePayload"
MEMBERSHIP_PAYLOAD_SCHEMA = f"{IDENTITY_SCHEMA}#/$defs/MembershipPayload"
INVITATION_PAYLOAD_SCHEMA = f"{IDENTITY_SCHEMA}#/$defs/InvitationPayload"
ENDPOINT_RECORD_TYPE = "shadow.profile.endpoint"
SPACE_RECORD_TYPE = "shadow.profile.space"
MEMBERSHIP_RECORD_TYPE = "shadow.profile.space-membership"
INVITATION_RECORD_TYPE = "shadow.profile.space-invitation"
RETENTION_REF = StableRecordRef(record_id="retention-default")


def _error(code: str, message: str, *, category: str = "validation", details: dict[str, Any] | None = None) -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))


def _digest_id(prefix: str, value: Any) -> str:
    return f"{prefix}-{sha256_digest(value)[7:39]}"


def _is_expired(value: str) -> bool:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) <= datetime.now(UTC)
    except ValueError:
        return True


@dataclass(frozen=True, slots=True)
class AccessContext:
    principal_ref: str
    space_id: str
    role: Literal["owner", "editor", "viewer"]
    endpoint_ref: str | None = None
    endpoint_trust: str = "paired"

    def can_read(self) -> bool:
        return self.role in {"owner", "editor", "viewer"}

    def can_write(self) -> bool:
        return self.role in {"owner", "editor"}

    def can_admin(self) -> bool:
        return self.role == "owner"


class IdentityService:
    """Canonical identity, endpoint and Space membership boundary for Phase 5."""

    def __init__(self, repository: CanonicalRepository, authority: CommitAuthority, registry: ContractRegistry) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def _commit(self, operations: list[CommitOperation], *, principal_ref: str, scope: str, key: str, digest: Any) -> list[dict[str, Any]]:
        if not self.repository.available:
            raise RepositoryUnavailable()
        result = self.authority.commit(
            CommitPlan(
                commit_request_id=f"commit-request-identity-{sha256_digest({'scope': scope, 'key': key})[7:31]}",
                idempotency_scope=scope,
                idempotency_key=key,
                request_digest=sha256_digest(digest),
                actor_ref=principal_ref,
                operations=operations,
                prepared_at=utc_timestamp(),
            )
        )
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Identity record version conflict.", category="conflict", details=result.model_dump(mode="json"))
        if result.outcome == "failed":
            structured = result.structured_error or {}
            if structured.get("code") == "shadow.repository.idempotency-mismatch":
                raise _error("shadow.repository.idempotency-mismatch", "Idempotency key was reused with different identity content.", category="conflict", details=structured)
            raise _error("shadow.identity.commit-failed", "Identity change could not be committed.", details=structured)
        return [self.repository.get(item.record_id, item.resulting_version) for item in result.operation_results if item.resulting_version]

    @staticmethod
    def _operation(*, record_id: str, record_type: str, schema: str, owner_ref: str, space_id: str, payload: dict[str, Any], operation: Literal["create", "update"], expected_version: int | None, actor: str) -> CommitOperation:
        return CommitOperation(
            operation_id=f"operation-{record_id}-{operation}",
            operation=operation,
            record_id=record_id,
            record_type=record_type,
            target_schema_ref=schema,
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=actor,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.user-command", origin_ref=f"identity-{record_id}"),
            retention_policy_ref=RETENTION_REF,
            typed_payload=payload,
            expected_version=expected_version,
        )

    def _records(self, record_type: str) -> list[dict[str, Any]]:
        rows = self.repository.query_heads(
            record_types={record_type},
            record_states={"active", "logically_deleted", "erased"},
            limit=None,
        )
        return [row for row in rows if row["record_state"] != "erased"]

    def _space(self, space_id: str) -> dict[str, Any] | None:
        row = self.repository.get(space_id)
        return row if row and row.get("record_type") == SPACE_RECORD_TYPE else None

    def role_for(self, principal_ref: str, space_id: str, endpoint_ref: str | None = None) -> AccessContext | None:
        endpoint_trust = "paired"
        if endpoint_ref:
            endpoint = self.repository.get(endpoint_ref)
            if endpoint is None and (self._space(space_id) is not None or self._records(ENDPOINT_RECORD_TYPE)):
                return None
            if endpoint and endpoint.get("record_type") == ENDPOINT_RECORD_TYPE:
                payload = endpoint["typed_payload"]
                if payload.get("principal_ref") != principal_ref or payload.get("lifecycle") != "active":
                    return None
                endpoint_trust = payload.get("trust", "untrusted")
                if endpoint_trust == "revoked":
                    return None
        space = self._space(space_id)
        if space and space["typed_payload"].get("owner_ref") == principal_ref and space["record_state"] == "active":
            return AccessContext(principal_ref, space_id, "owner", endpoint_ref, endpoint_trust)
        if not space and space_id == "space-personal" and principal_ref == "principal-local":
            return AccessContext(principal_ref, space_id, "owner", endpoint_ref, endpoint_trust)
        # Preserve the pre-Phase-5 local-dev contract until the first explicit Space
        # or Membership is created in a repository. Once identity records exist,
        # unknown Spaces are deny-by-default.
        if not self._records(SPACE_RECORD_TYPE) and not self._records(MEMBERSHIP_RECORD_TYPE):
            return AccessContext(principal_ref, space_id, "owner", endpoint_ref, endpoint_trust)
        for row in self._records(MEMBERSHIP_RECORD_TYPE):
            payload = row["typed_payload"]
            if payload.get("space_id") == space_id and payload.get("principal_ref") == principal_ref and payload.get("lifecycle") == "active":
                return AccessContext(principal_ref, space_id, payload["role"], endpoint_ref, endpoint_trust)
        return None

    def require(self, principal_ref: str, space_id: str, *, endpoint_ref: str | None = None, write: bool = False, admin: bool = False) -> AccessContext:
        context = self.role_for(principal_ref, space_id, endpoint_ref)
        if context is None or (admin and not context.can_admin()) or (write and not context.can_write()):
            raise _error("shadow.space.membership-denied", "The principal is not authorized for this Space operation.", category="unauthorized", details={"principal_ref": principal_ref, "space_id": space_id})
        return context

    def pair_endpoint(self, *, principal_ref: str, space_id: str, endpoint_ref: str, endpoint_kind: str, label: str | None, capabilities: list[str], idempotency_key: str) -> dict[str, Any]:
        self.require(principal_ref, space_id, write=True)
        record_id = endpoint_ref
        current = self.repository.get(record_id)
        scope = f"endpoint:{principal_ref}:{space_id}"
        prior = self.repository.idempotency_result(scope, idempotency_key)
        token = f"pair-{sha256_digest({'principal': principal_ref, 'endpoint': endpoint_ref, 'key': idempotency_key})[7:39]}"
        payload = {
            "endpoint_ref": endpoint_ref, "principal_ref": principal_ref, "endpoint_kind": endpoint_kind,
            "trust": "paired", "lifecycle": "active", "capabilities": sorted(set(capabilities)),
            "paired_at": utc_timestamp(),
        }
        if label:
            payload["label"] = label
        operation = self._operation(record_id=record_id, record_type=ENDPOINT_RECORD_TYPE, schema=ENDPOINT_PAYLOAD_SCHEMA, owner_ref=principal_ref, space_id=space_id, payload=payload, operation="create" if current is None else "update", expected_version=None if current is None else current["version"], actor=principal_ref)
        request_digest = {"endpoint_ref": endpoint_ref, "endpoint_kind": endpoint_kind, "label": label, "capabilities": sorted(set(capabilities))}
        record = self._commit([operation], principal_ref=principal_ref, scope=scope, key=idempotency_key, digest=request_digest)[0]
        return {"endpoint": record, "pairing_token": token, "replayed": prior is not None}

    def revoke_endpoint(self, *, principal_ref: str, endpoint_ref: str, expected_version: int, idempotency_key: str) -> dict[str, Any]:
        endpoint = self.repository.get(endpoint_ref)
        if not endpoint or endpoint.get("record_type") != ENDPOINT_RECORD_TYPE:
            raise _error("shadow.identity.endpoint-not-found", "Endpoint was not found.")
        if endpoint["typed_payload"].get("principal_ref") != principal_ref:
            raise _error("shadow.identity.unauthorized", "Only the endpoint owner can revoke it.", category="unauthorized")
        payload = dict(endpoint["typed_payload"])
        payload.update({"trust": "revoked", "lifecycle": "revoked", "revoked_at": utc_timestamp()})
        record = self._commit([self._operation(record_id=endpoint_ref, record_type=ENDPOINT_RECORD_TYPE, schema=ENDPOINT_PAYLOAD_SCHEMA, owner_ref=endpoint["owner_ref"], space_id=endpoint["space_id"], payload=payload, operation="update", expected_version=expected_version, actor=principal_ref)], principal_ref=principal_ref, scope=f"endpoint:{principal_ref}:{endpoint['space_id']}", key=idempotency_key, digest={"endpoint_ref": endpoint_ref, "expected_version": expected_version, "operation": "revoke"})[0]
        return {"endpoint": record, "replayed": record and record["version"] == expected_version}

    def create_space(self, *, principal_ref: str, space_id: str, display_name: str, idempotency_key: str) -> dict[str, Any]:
        space_payload = {"space_id": space_id, "display_name": display_name, "space_kind": "shared", "owner_ref": principal_ref, "lifecycle": "active"}
        scope = f"space:{principal_ref}"
        request_digest = sha256_digest({"space": space_payload, "membership": {"principal_ref": principal_ref}})
        prior = self.repository.idempotency_result(scope, idempotency_key)
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise _error("shadow.repository.idempotency-mismatch", "Space idempotency key was reused with different content.", category="conflict")
            membership_id = _digest_id("membership", {"space": space_id, "principal": principal_ref})
            return {"space": self.repository.get(space_id), "membership": self.repository.get(membership_id), "replayed": True}
        if self.repository.get(space_id) is not None:
            raise _error("shadow.space.already-exists", "Space already exists.", category="conflict")
        membership_payload = {"space_id": space_id, "principal_ref": principal_ref, "role": "owner", "lifecycle": "active", "granted_by": principal_ref, "granted_at": utc_timestamp()}
        membership_id = _digest_id("membership", {"space": space_id, "principal": principal_ref})
        operations = [
            self._operation(record_id=space_id, record_type=SPACE_RECORD_TYPE, schema=SPACE_PAYLOAD_SCHEMA, owner_ref=principal_ref, space_id=space_id, payload=space_payload, operation="create", expected_version=None, actor=principal_ref),
            self._operation(record_id=membership_id, record_type=MEMBERSHIP_RECORD_TYPE, schema=MEMBERSHIP_PAYLOAD_SCHEMA, owner_ref=principal_ref, space_id=space_id, payload=membership_payload, operation="create", expected_version=None, actor=principal_ref),
        ]
        records = self._commit(operations, principal_ref=principal_ref, scope=scope, key=idempotency_key, digest={"space": space_payload, "membership": {"principal_ref": principal_ref}})
        return {"space": records[0], "membership": records[1], "replayed": False}

    def list_spaces(self, principal_ref: str) -> list[dict[str, Any]]:
        spaces = {row["record_id"]: row for row in self._records(SPACE_RECORD_TYPE)}
        allowed = {row["typed_payload"]["space_id"] for row in self._records(MEMBERSHIP_RECORD_TYPE) if row["typed_payload"].get("principal_ref") == principal_ref and row["typed_payload"].get("lifecycle") == "active"}
        allowed.update(row["record_id"] for row in spaces.values() if row["typed_payload"].get("owner_ref") == principal_ref)
        if principal_ref == "principal-local":
            allowed.add("space-personal")
        result = [row for key, row in spaces.items() if key in allowed]
        if "space-personal" in allowed and "space-personal" not in spaces:
            result.insert(0, {
                "record_id": "space-personal",
                "record_type": SPACE_RECORD_TYPE,
                "version": 1,
                "owner_ref": principal_ref,
                "space_id": "space-personal",
                "typed_payload": {
                    "space_id": "space-personal",
                    "display_name": "Personal Space",
                    "space_kind": "personal",
                    "owner_ref": principal_ref,
                    "lifecycle": "active",
                },
            })
        return result

    def list_members(self, *, principal_ref: str, space_id: str) -> list[dict[str, Any]]:
        self.require(principal_ref, space_id)
        return [row for row in self._records(MEMBERSHIP_RECORD_TYPE) if row["typed_payload"].get("space_id") == space_id and row["typed_payload"].get("lifecycle") == "active"]

    def invite(self, *, principal_ref: str, space_id: str, invitee_ref: str, role: Literal["editor", "viewer"], expires_at: str, idempotency_key: str) -> dict[str, Any]:
        self.require(principal_ref, space_id, admin=True)
        if _is_expired(expires_at):
            raise _error("shadow.space.invitation-invalid", "Invitation expiry must be in the future.")
        token = f"invite-{sha256_digest({'space': space_id, 'invitee': invitee_ref, 'key': idempotency_key})[7:39]}"
        payload = {"space_id": space_id, "invitation_digest": sha256_digest(token), "invitee_ref": invitee_ref, "role": role, "status": "pending", "expires_at": expires_at, "invited_by": principal_ref}
        invitation_id = _digest_id("invitation", {"space": space_id, "invitee": invitee_ref, "digest": payload["invitation_digest"]})
        record = self._commit([self._operation(record_id=invitation_id, record_type=INVITATION_RECORD_TYPE, schema=INVITATION_PAYLOAD_SCHEMA, owner_ref=principal_ref, space_id=space_id, payload=payload, operation="create", expected_version=None, actor=principal_ref)], principal_ref=principal_ref, scope=f"invitation:{space_id}", key=idempotency_key, digest={"space_id": space_id, "invitee_ref": invitee_ref, "role": role, "expires_at": expires_at})[0]
        return {"invitation": record, "invitation_token": token, "replayed": False}

    def accept_invitation(self, *, principal_ref: str, invitation_id: str, invitation_token: str, idempotency_key: str) -> dict[str, Any]:
        invitation = self.repository.get(invitation_id)
        if not invitation or invitation.get("record_type") != INVITATION_RECORD_TYPE:
            raise _error("shadow.space.invitation-invalid", "Invitation was not found.")
        payload = invitation["typed_payload"]
        scope = f"invitation:{payload.get('space_id', invitation['space_id'])}"
        prior = self.repository.idempotency_result(scope, idempotency_key)
        if prior is not None:
            if prior["request_digest"] != sha256_digest({"invitation_id": invitation_id, "invitation_token": invitation_token}):
                raise _error("shadow.repository.idempotency-mismatch", "Invitation idempotency key was reused with different content.", category="conflict")
            membership_id = _digest_id("membership", {"space": payload["space_id"], "principal": principal_ref})
            return {"membership": self.repository.get(membership_id), "invitation": invitation, "replayed": True}
        if payload.get("invitee_ref") != principal_ref or payload.get("status") != "pending" or _is_expired(payload["expires_at"]):
            raise _error("shadow.space.invitation-invalid", "Invitation is expired, revoked, or addressed to another principal.", category="unauthorized")
        if sha256_digest(invitation_token) != payload.get("invitation_digest"):
            raise _error("shadow.space.invitation-invalid", "Invitation token is invalid.", category="unauthorized")
        membership_id = _digest_id("membership", {"space": payload["space_id"], "principal": principal_ref})
        membership = self.repository.get(membership_id)
        membership_payload = {"space_id": payload["space_id"], "principal_ref": principal_ref, "role": payload["role"], "lifecycle": "active", "granted_by": payload["invited_by"], "granted_at": utc_timestamp()}
        invitation_payload = dict(payload)
        invitation_payload.update({"status": "accepted", "accepted_at": utc_timestamp()})
        operations = [
            self._operation(record_id=membership_id, record_type=MEMBERSHIP_RECORD_TYPE, schema=MEMBERSHIP_PAYLOAD_SCHEMA, owner_ref=payload["invited_by"], space_id=payload["space_id"], payload=membership_payload, operation="create" if membership is None else "update", expected_version=None if membership is None else membership["version"], actor=principal_ref),
            self._operation(record_id=invitation_id, record_type=INVITATION_RECORD_TYPE, schema=INVITATION_PAYLOAD_SCHEMA, owner_ref=invitation["owner_ref"], space_id=invitation["space_id"], payload=invitation_payload, operation="update", expected_version=invitation["version"], actor=principal_ref),
        ]
        records = self._commit(operations, principal_ref=principal_ref, scope=scope, key=idempotency_key, digest={"invitation_id": invitation_id, "invitation_token": invitation_token})
        return {"membership": records[0], "invitation": records[1], "replayed": False}

    def revoke_member(self, *, principal_ref: str, space_id: str, target_principal: str, expected_version: int, idempotency_key: str) -> dict[str, Any]:
        self.require(principal_ref, space_id, admin=True)
        membership_id = _digest_id("membership", {"space": space_id, "principal": target_principal})
        membership = self.repository.get(membership_id)
        if not membership or membership["typed_payload"].get("lifecycle") != "active":
            raise _error("shadow.space.membership-not-found", "Membership was not found.")
        payload = dict(membership["typed_payload"])
        payload.update({"lifecycle": "revoked", "revoked_at": utc_timestamp()})
        record = self._commit([self._operation(record_id=membership_id, record_type=MEMBERSHIP_RECORD_TYPE, schema=MEMBERSHIP_PAYLOAD_SCHEMA, owner_ref=membership["owner_ref"], space_id=space_id, payload=payload, operation="update", expected_version=expected_version, actor=principal_ref)], principal_ref=principal_ref, scope=f"space:{space_id}", key=idempotency_key, digest={"space_id": space_id, "target_principal": target_principal, "expected_version": expected_version, "operation": "revoke"})[0]
        return {"membership": record, "replayed": False}
