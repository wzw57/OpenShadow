from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from shadow_kernel.ids import sha256_digest

PERIPHERAL_SCHEMA = "https://schemas.openshadow.dev/contracts/peripheral/1.0.0"


@dataclass(frozen=True, slots=True)
class InteractionRequest:
    operation: str
    principal_ref: str
    space_id: str
    endpoint_ref: str
    capability_ref: str
    consent_ref: str
    data_classification: Literal["public", "personal", "sensitive", "restricted"]
    expires_at: str
    idempotency_key: str
    typed_input: Any
    secret_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True, slots=True)
class AdapterResult:
    status: Literal["succeeded", "failed", "unknown"]
    request_digest: str
    external_ref: str | None = None
    result_digest: str | None = None
    reason: str | None = None
    replayed: bool = False


class PeripheralAdapter(Protocol):
    def execute(self, request: InteractionRequest) -> AdapterResult: ...


def validate_interaction(request: InteractionRequest, *, now: datetime | None = None) -> None:
    if not request.principal_ref or not request.space_id or not request.endpoint_ref:
        raise ValueError("principal_ref, space_id and endpoint_ref are required")
    if not request.capability_ref or not request.consent_ref:
        raise ValueError("capability_ref and consent_ref are required")
    if datetime.fromisoformat(request.expires_at.replace("Z", "+00:00")) <= (now or datetime.now(UTC)):
        raise ValueError("interaction consent/capability has expired")
    if request.secret_ref is not None and not any(request.secret_ref.startswith(prefix) for prefix in ("env:", "vault:", "keychain:", "opaque:")):
        raise ValueError("secret_ref must be an opaque resolver reference")
    serialized = str(request.typed_input).lower()
    if any(marker in serialized for marker in ("api_key", "access_token", "authorization", "inline_secret")):
        raise ValueError("inline Secret material is not accepted")


class DeterministicPeripheralAdapter:
    """Contract adapter: validates boundaries and never calls a real device/provider."""

    def __init__(self, *, supported_capabilities: set[str] | None = None, consent_valid: bool = True, outcome: str = "succeeded") -> None:
        self.supported_capabilities = supported_capabilities or set()
        self.consent_valid = consent_valid
        self.outcome = outcome
        self.calls = 0
        self._receipts: dict[str, tuple[str, AdapterResult]] = {}

    def execute(self, request: InteractionRequest) -> AdapterResult:
        validate_interaction(request)
        if request.capability_ref not in self.supported_capabilities:
            raise PermissionError("capability is not supported")
        if not self.consent_valid:
            raise PermissionError("consent is revoked or invalid")
        digest = sha256_digest(request.as_dict())
        prior = self._receipts.get(request.idempotency_key)
        if prior is not None:
            if prior[0] != digest:
                raise ValueError("idempotency key was used for a different interaction")
            return AdapterResult(**{**asdict(prior[1]), "replayed": True})
        self.calls += 1
        result = AdapterResult(
            status=self.outcome if self.outcome in {"succeeded", "failed", "unknown"} else "unknown",
            request_digest=digest,
            external_ref=f"deterministic-interaction:{digest[7:31]}",
            result_digest=sha256_digest({"operation": request.operation, "input": request.typed_input}) if self.outcome == "succeeded" else None,
            reason=None if self.outcome == "succeeded" else "deterministic adapter outcome",
        )
        self._receipts[request.idempotency_key] = (digest, result)
        return result


__all__ = ["AdapterResult", "DeterministicPeripheralAdapter", "InteractionRequest", "PeripheralAdapter", "validate_interaction"]
