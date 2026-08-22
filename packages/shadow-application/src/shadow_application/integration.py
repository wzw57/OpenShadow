from __future__ import annotations

import re
from typing import Any, Literal

from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import Field, model_validator
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    Provenance,
    RecordVersionRef,
    StableRecordRef,
    StrictModel,
)
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

INTEGRATION_SCHEMA = "https://schemas.openshadow.dev/contracts/integrations/1.0.0"
INTEGRATION_PAYLOAD_SCHEMA = f"{INTEGRATION_SCHEMA}#/$defs/IntegrationPayload"
INTEGRATION_RECORD_TYPE = "shadow.profile.integration"
_SECRET_PATTERN = re.compile(
    r"(?i)(?:password|token|secret|private[_-]?key|authorization)\s*[:=]"
)


class IntegrationRegistrationRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    integration_id: str = Field(min_length=1, max_length=80)
    provider_kind: str = Field(min_length=1, max_length=200)
    external_ref: str = Field(min_length=1, max_length=1000)
    config_ref: StableRecordRef
    secret_refs: list[StableRecordRef] = Field(default_factory=list, max_length=100)
    adapter_ref: RecordVersionRef
    adapter_descriptor_digest: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$", min_length=71, max_length=71
    )
    status: Literal["enabled", "disabled", "unavailable", "needs_reauth"] = "disabled"
    lifecycle: Literal["active", "retired"] = "active"
    health_observation_ref: RecordVersionRef | None = None
    data_classification: Literal["public", "personal", "sensitive", "restricted"] = "personal"
    operation: Literal["create", "refresh"] = "create"
    expected_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_request(self) -> IntegrationRegistrationRequest:
        if self.operation == "create" and self.expected_version is not None:
            raise ValueError("create cannot include expected_version")
        if self.operation == "refresh" and self.expected_version is None:
            raise ValueError("refresh requires expected_version")
        refs = [ref.record_id for ref in self.secret_refs]
        if len(refs) != len(set(refs)):
            raise ValueError("secret_refs must be unique")
        if _SECRET_PATTERN.search(self.external_ref):
            raise ValueError("external_ref cannot contain secret material")
        return self


class IntegrationRegistrationResult(StrictModel):
    result_state: Literal["committed", "replayed"]
    integration_id: str
    record_ref: RecordVersionRef
    adapter_descriptor_digest: str
    commit_id: str | None = None
    replayed: bool = False
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)


def integration_result_digest(result: IntegrationRegistrationResult) -> str:
    return sha256_digest(
        {
            "integration_id": result.integration_id,
            "record_ref": result.record_ref.model_dump(mode="json"),
            "adapter_descriptor_digest": result.adapter_descriptor_digest,
            "commit_id": result.commit_id,
        }
    )


class IntegrationService:
    """Register and refresh an external Integration without performing provider side effects."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def register(self, request: IntegrationRegistrationRequest) -> IntegrationRegistrationResult:
        request = IntegrationRegistrationRequest.model_validate(request)
        if not self.repository.available:
            raise RepositoryUnavailable()
        payload = {
            "integration_id": request.integration_id,
            "format": "shadow.integration",
            "provider_kind": request.provider_kind,
            "external_ref": request.external_ref,
            "config_ref": request.config_ref.model_dump(mode="json"),
            "secret_refs": [ref.model_dump(mode="json") for ref in request.secret_refs],
            "adapter_ref": request.adapter_ref.model_dump(mode="json"),
            "adapter_descriptor_digest": request.adapter_descriptor_digest,
            "status": request.status,
            "lifecycle": request.lifecycle,
        }
        if request.health_observation_ref is not None:
            payload["health_observation_ref"] = request.health_observation_ref.model_dump(mode="json")
        try:
            self.registry.validate(payload, INTEGRATION_PAYLOAD_SCHEMA)
        except JsonSchemaValidationError as exc:
            raise _invalid("Integration payload does not satisfy its contract.") from exc

        record_id = _integration_record_id(request.integration_id)
        current = self.repository.get(record_id)
        if current is not None and (
            current["owner_ref"] != request.principal_ref or current["space_id"] != request.space_id
        ):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.integration.owner-space-mismatch",
                    category="unauthorized",
                    message="Integration owner or space does not match the registration principal.",
                    typed_details={"record_id": record_id},
                )
            )
        if request.operation == "refresh":
            if current is None:
                raise _invalid("Integration refresh target was not found.", {"record_id": record_id})
            if current["record_type"] != INTEGRATION_RECORD_TYPE:
                raise _invalid("Integration identity is occupied by another record type.", {"record_id": record_id})
            if current["record_state"] != "active" or current["typed_payload"].get("lifecycle") != "active":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.integration.not-active",
                        category="conflict",
                        message="A retired Integration cannot be refreshed.",
                        typed_details={"record_id": record_id, "current_version": current["version"]},
                    )
                )

        operation = CommitOperation(
            operation_id=f"operation-{record_id}-{request.operation}-{request.idempotency_key}",
            operation="create" if request.operation == "create" else "update",
            record_id=record_id,
            record_type=INTEGRATION_RECORD_TYPE,
            target_schema_ref=INTEGRATION_PAYLOAD_SCHEMA,
            owner_ref=request.principal_ref,
            space_id=request.space_id,
            created_by=request.principal_ref,
            data_classification=request.data_classification,
            provenance=Provenance(
                origin_type="shadow.origin.user-command",
                origin_ref=f"integration-registration-{request.integration_id}",
            ),
            retention_policy_ref=StableRecordRef(record_id="retention-default"),
            typed_payload=payload,
            expected_version=request.expected_version,
        )
        try:
            commit = self.authority.commit(
                CommitPlan(
                    commit_request_id=f"commit-request-{record_id}-{request.idempotency_key}",
                    idempotency_scope=f"integration:{request.principal_ref}:{request.space_id}",
                    idempotency_key=request.idempotency_key,
                    request_digest=sha256_digest(request.model_dump(mode="json", exclude_none=True)),
                    actor_ref=request.principal_ref,
                    operations=[operation],
                    prepared_at=utc_timestamp(),
                )
            )
        except RepositoryUnavailable:
            raise

        if commit.outcome == "conflict":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.integration.version-conflict",
                    category="conflict",
                    message="Integration expected version does not match the current head.",
                    typed_details=commit.model_dump(mode="json", exclude_none=True),
                )
            )
        if commit.outcome == "failed":
            structured = commit.structured_error or {}
            if structured.get("code") == "shadow.repository.idempotency-mismatch":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.integration.replay-conflict",
                        category="conflict",
                        message="Integration idempotency key was reused with different content.",
                        typed_details=structured,
                    )
                )
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.integration.commit-failed",
                    category="validation",
                    message="Integration could not be committed.",
                    typed_details=structured,
                )
            )

        operation_result = commit.operation_results[0]
        if operation_result.resulting_version is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.integration.commit-missing-result",
                    category="internal",
                    message="Integration commit did not return a resulting version.",
                )
            )
        result = IntegrationRegistrationResult(
            result_state="replayed" if commit.outcome == "idempotent_replay" else "committed",
            integration_id=request.integration_id,
            record_ref=RecordVersionRef(
                record_id=record_id, version=operation_result.resulting_version
            ),
            adapter_descriptor_digest=request.adapter_descriptor_digest,
            commit_id=commit.commit_id,
            replayed=commit.outcome == "idempotent_replay",
        )
        return result.model_copy(update={"result_digest": integration_result_digest(result)})


def _integration_record_id(integration_id: str) -> str:
    return f"integration-{sha256_digest({'integration_id': integration_id})[7:39]}"


def _invalid(message: str, details: dict[str, Any] | None = None) -> ShadowDomainError:
    return ShadowDomainError(
        ShadowError(
            code="shadow.integration.invalid",
            category="validation",
            message=message,
            typed_details=details,
        )
    )


__all__ = [
    "IntegrationRegistrationRequest",
    "IntegrationRegistrationResult",
    "IntegrationService",
    "integration_result_digest",
]
