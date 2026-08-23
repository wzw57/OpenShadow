from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import jwt
from jwt import PyJWKClient
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

AUTH_SCHEMA = "https://schemas.openshadow.dev/contracts/auth/1.0.0"
SESSION_SCHEMA = f"{AUTH_SCHEMA}#/$defs/SessionPayload"
SESSION_RECORD_TYPE = "shadow.security.session"
RETENTION_REF = StableRecordRef(record_id="retention-security-default")


def _error(code: str, message: str, *, category: str = "validation", retryable: bool = False, details: Any | None = None) -> ShadowDomainError:
    return ShadowDomainError(
        ShadowError(code=code, category=category, message=message, retryable=retryable, typed_details=details)
    )


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (TypeError, ValueError) as exc:
        raise _error("shadow.auth.invalid-time", "Authentication timestamp is invalid.") from exc


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    principal_ref: str
    issuer: str
    subject: str
    audience: str
    auth_method: str
    issued_at: str
    expires_at: str
    claims_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "principal_ref": self.principal_ref,
            "issuer": self.issuer,
            "subject": self.subject,
            "audience": self.audience,
            "auth_method": self.auth_method,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "claims_digest": self.claims_digest,
        }


@dataclass(frozen=True, slots=True)
class AuthContext:
    principal_ref: str
    issuer: str
    audience: str
    auth_method: str
    authenticated_at: str
    expires_at: str
    session_ref: str
    endpoint_ref: str | None = None
    claims_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "principal_ref": self.principal_ref,
            "issuer": self.issuer,
            "audience": self.audience,
            "auth_method": self.auth_method,
            "authenticated_at": self.authenticated_at,
            "expires_at": self.expires_at,
            "session_ref": self.session_ref,
            "endpoint_ref": self.endpoint_ref,
            "claims_digest": self.claims_digest,
        }


class AuthVerifier(Protocol):
    def verify(self, credential: str) -> VerifiedIdentity: ...


@dataclass(frozen=True, slots=True)
class SecretLease:
    secret_ref: str
    purpose: str
    value: str
    lease_expires_at: str


class SecretResolver(Protocol):
    def resolve(self, secret_ref: str, *, purpose: str) -> SecretLease: ...


class EnvironmentSecretResolver:
    """Development-safe resolver; production deployments should replace this port."""

    def resolve(self, secret_ref: str, *, purpose: str) -> SecretLease:
        if not secret_ref.startswith("env:"):
            raise _error("shadow.auth.secret-ref-unsupported", "Only env secret references are available in this adapter.", category="unsupported")
        variable = secret_ref[4:]
        value = os.getenv(variable, "")
        if not value:
            raise _error("shadow.auth.secret-unavailable", "Configured authentication secret is unavailable.", category="unavailable", retryable=True)
        return SecretLease(secret_ref, purpose, value, utc_timestamp())


class StaticSecretResolver:
    """In-memory resolver used only by local-dev/test composition roots."""

    def __init__(self, value: str, *, secret_ref: str = "memory:local-dev") -> None:
        self.value = value
        self.secret_ref = secret_ref

    def resolve(self, secret_ref: str, *, purpose: str) -> SecretLease:
        if secret_ref != self.secret_ref or not self.value:
            raise _error("shadow.auth.secret-unavailable", "Configured authentication secret is unavailable.", category="unavailable", retryable=True)
        return SecretLease(secret_ref, purpose, self.value, utc_timestamp())


class DeterministicAuthVerifier:
    """Explicit local-dev verifier; it must never be selected in production mode."""

    def verify(self, credential: str) -> VerifiedIdentity:
        if not credential.startswith("local:"):
            raise _error("shadow.auth.invalid-credential", "Local authentication credential is invalid.", category="unauthorized")
        principal = credential[6:].strip()
        if not principal or len(principal) > 255 or any(char.isspace() for char in principal):
            raise _error("shadow.auth.invalid-credential", "Local authentication credential is invalid.", category="unauthorized")
        now = datetime.now(UTC)
        return VerifiedIdentity(
            principal_ref=principal,
            issuer="local-dev",
            subject=principal,
            audience="openshadow",
            auth_method="deterministic",
            issued_at=now.isoformat().replace("+00:00", "Z"),
            expires_at=(now + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
            claims_digest=sha256_digest({"issuer": "local-dev", "subject": principal}),
        )


class OidcAuthVerifier:
    """Generic JWT/JWKS verifier; issuer-specific login remains outside Shadow Core."""

    def __init__(self, *, issuer: str, audience: str, jwks_url: str, algorithms: list[str] | None = None) -> None:
        if not issuer or not audience or not jwks_url:
            raise ValueError("OIDC issuer, audience and jwks_url are required")
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self._jwks = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)

    def verify(self, credential: str) -> VerifiedIdentity:
        token = credential.removeprefix("Bearer ").strip()
        if not token or token.count(".") != 2:
            raise _error("shadow.auth.invalid-credential", "Bearer credential is invalid.", category="unauthorized")
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["sub", "iss", "aud", "iat", "exp"]},
            )
        except Exception as exc:
            raise _error("shadow.auth.invalid-credential", "Bearer credential could not be verified.", category="unauthorized") from exc
        subject = str(claims["sub"])
        audience = claims["aud"]
        if isinstance(audience, list):
            audience = ",".join(str(item) for item in audience)
        principal_ref = f"principal-{sha256_digest({'issuer': self.issuer, 'subject': subject})[7:39]}"
        return VerifiedIdentity(
            principal_ref=principal_ref,
            issuer=self.issuer,
            subject=subject,
            audience=str(audience),
            auth_method="oidc",
            issued_at=datetime.fromtimestamp(int(claims["iat"]), UTC).isoformat().replace("+00:00", "Z"),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), UTC).isoformat().replace("+00:00", "Z"),
            claims_digest=sha256_digest(claims),
        )


class SessionService:
    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
        secret_resolver: SecretResolver,
        *,
        secret_ref: str = "env:SHADOW_AUTH_SESSION_SECRET",
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry
        self.secret_resolver = secret_resolver
        self.secret_ref = secret_ref

    def _secret(self) -> str:
        return self.secret_resolver.resolve(self.secret_ref, purpose="auth-session-signing").value

    def _sign(self, payload: dict[str, Any]) -> str:
        body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = hmac.new(self._secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{_b64(signature)}"

    def _decode(self, token: str) -> dict[str, Any]:
        try:
            body, signature = token.split(".", 1)
            expected = hmac.new(self._secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_unb64(signature), expected):
                raise ValueError("signature")
            payload = json.loads(_unb64(body).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload")
            return payload
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise _error("shadow.auth.invalid-credential", "Session credential is invalid.", category="unauthorized") from exc

    @staticmethod
    def _operation(record_id: str, payload: dict[str, Any], *, owner_ref: str, operation: str, expected_version: int | None, actor_ref: str) -> CommitOperation:
        return CommitOperation(
            operation_id=f"operation-{record_id}-{operation}",
            operation=operation,  # type: ignore[arg-type]
            record_id=record_id,
            record_type=SESSION_RECORD_TYPE,
            target_schema_ref=SESSION_SCHEMA,
            owner_ref=owner_ref,
            space_id="space-personal",
            created_by=actor_ref,
            data_classification="sensitive",
            provenance=Provenance(origin_type="shadow.origin.auth", origin_ref=f"auth-{record_id}"),
            retention_policy_ref=RETENTION_REF,
            typed_payload=payload,
            expected_version=expected_version,
        )

    def create_session(self, identity: VerifiedIdentity, *, idempotency_key: str, ttl_seconds: int = 3600, endpoint_ref: str | None = None) -> dict[str, Any]:
        if ttl_seconds < 60 or ttl_seconds > 86_400:
            raise _error("shadow.auth.session-ttl-invalid", "Session TTL must be between 60 and 86400 seconds.")
        if not self.repository.available:
            raise RepositoryUnavailable()
        session_seed = {"principal": identity.principal_ref, "issuer": identity.issuer, "subject": identity.subject, "key": idempotency_key}
        nonce = sha256_digest(session_seed)[7:39]
        session_ref = f"auth-session-{nonce}"
        request_digest = sha256_digest({"identity": identity.as_dict(), "ttl_seconds": ttl_seconds, "endpoint_ref": endpoint_ref})
        prior = self.repository.idempotency_result(f"auth-session:{identity.principal_ref}", idempotency_key)
        current = self.repository.get(session_ref)
        if prior is not None:
            if prior.get("request_digest") != request_digest:
                raise _error("shadow.repository.idempotency-mismatch", "The idempotency key was already used for a different request.", category="conflict")
            if current is None:
                raise _error("shadow.auth.session-not-found", "The idempotent session receipt has no canonical session record.", category="conflict")
            stored = current["typed_payload"]
            token = self._sign({"session_ref": session_ref, "nonce": nonce, "principal_ref": stored["principal_ref"], "issuer": stored["issuer"], "audience": stored["audience"], "issued_at": stored["issued_at"], "expires_at": stored["expires_at"], "endpoint_ref": stored.get("endpoint_ref")})
            if stored.get("token_digest") != sha256_digest(token):
                raise _error("shadow.auth.session-integrity-failed", "The canonical session token digest does not match the idempotent replay.", category="conflict")
            return {"session": current, "token": token, "context": self._context_from_payload(stored, session_ref), "replayed": True}
        if current is not None:
            raise _error("shadow.auth.session-conflict", "The deterministic session reference already exists.", category="conflict")
        issued_at = utc_timestamp()
        expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
        payload = {
            "session_ref": session_ref,
            "principal_ref": identity.principal_ref,
            "issuer": identity.issuer,
            "audience": identity.audience,
            "token_digest": "sha256:" + "0" * 64,
            "claims_digest": identity.claims_digest,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "lifecycle": "active",
            "auth_method": identity.auth_method,
            "endpoint_ref": endpoint_ref,
        }
        token = self._sign({"session_ref": session_ref, "nonce": nonce, "principal_ref": identity.principal_ref, "issuer": identity.issuer, "audience": identity.audience, "issued_at": issued_at, "expires_at": expires_at, "endpoint_ref": endpoint_ref})
        payload["token_digest"] = sha256_digest(token)
        operation = self._operation(session_ref, payload, owner_ref=identity.principal_ref, operation="create" if current is None else "update", expected_version=None if current is None else current["version"], actor_ref=identity.principal_ref)
        result = self.authority.commit(CommitPlan(commit_request_id=f"commit-request-{session_ref}", idempotency_scope=f"auth-session:{identity.principal_ref}", idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=identity.principal_ref, operations=[operation], prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.auth.session-conflict", "Session version conflict.", category="conflict", details=result.model_dump(mode="json"))
        if result.outcome == "failed":
            raise _error("shadow.auth.session-commit-failed", "Session could not be committed.", details=result.structured_error)
        record = self.repository.get(session_ref, result.operation_results[0].resulting_version)
        context = self._context_from_payload(payload, session_ref)
        return {"session": record, "token": token, "context": context, "replayed": result.outcome == "idempotent_replay"}

    def revoke(self, context: AuthContext, *, idempotency_key: str, reason: str = "logout") -> dict[str, Any]:
        if not self.repository.available:
            raise RepositoryUnavailable()
        current = self.repository.get(context.session_ref)
        if not current or current.get("record_type") != SESSION_RECORD_TYPE:
            raise _error("shadow.auth.session-not-found", "Session was not found.", category="unauthorized")
        if current["typed_payload"].get("principal_ref") != context.principal_ref:
            raise _error("shadow.auth.context-mismatch", "Session principal does not match the request context.", category="unauthorized")
        payload = dict(current["typed_payload"])
        payload.update({"lifecycle": "revoked", "revoked_at": utc_timestamp(), "revocation_reason": reason})
        operation = self._operation(context.session_ref, payload, owner_ref=context.principal_ref, operation="update", expected_version=current["version"], actor_ref=context.principal_ref)
        result = self.authority.commit(CommitPlan(commit_request_id=f"commit-request-revoke-{context.session_ref}", idempotency_scope=f"auth-session:{context.principal_ref}:revoke", idempotency_key=idempotency_key, request_digest=sha256_digest({"session_ref": context.session_ref, "reason": reason}), actor_ref=context.principal_ref, operations=[operation], prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.auth.session-conflict", "Session revoke conflicted with another change.", category="conflict", details=result.model_dump(mode="json"))
        if result.outcome == "failed":
            raise _error("shadow.auth.revoke-failed", "Session revoke could not be committed.", details=result.structured_error)
        return {"session": self.repository.get(context.session_ref, result.operation_results[0].resulting_version), "replayed": result.outcome == "idempotent_replay"}

    def verify_session(self, token: str) -> AuthContext:
        payload = self._decode(token)
        session_ref = str(payload.get("session_ref", ""))
        record = self.repository.get(session_ref)
        if not record or record.get("record_type") != SESSION_RECORD_TYPE:
            raise _error("shadow.auth.session-revoked", "Session is not active.", category="unauthorized")
        stored = record["typed_payload"]
        if stored.get("lifecycle") != "active" or stored.get("token_digest") != sha256_digest(token):
            raise _error("shadow.auth.session-revoked", "Session is not active.", category="unauthorized")
        if _parse_time(str(stored["expires_at"])) <= datetime.now(UTC):
            raise _error("shadow.auth.session-expired", "Session has expired.", category="unauthorized")
        if payload.get("principal_ref") != stored.get("principal_ref") or payload.get("issuer") != stored.get("issuer"):
            raise _error("shadow.auth.context-mismatch", "Session context does not match its canonical record.", category="unauthorized")
        return self._context_from_payload(stored, session_ref)

    @staticmethod
    def _context_from_payload(payload: dict[str, Any], session_ref: str) -> AuthContext:
        return AuthContext(
            principal_ref=payload["principal_ref"], issuer=payload["issuer"], audience=payload["audience"],
            auth_method=payload["auth_method"], authenticated_at=payload["issued_at"], expires_at=payload["expires_at"],
            session_ref=session_ref, endpoint_ref=payload.get("endpoint_ref"), claims_digest=payload.get("claims_digest"),
        )
