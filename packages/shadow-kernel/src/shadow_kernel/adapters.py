from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .errors import ShadowDomainError, ShadowError
from .ids import sha256_digest, utc_timestamp


class AdapterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityDeclaration(AdapterModel):
    capability_id: str
    capability_version: str
    contract_ref: str
    declaration_schema_ref: str | None = None
    typed_parameters: Any | None = None


class AdapterDescriptor(AdapterModel):
    descriptor_id: str
    descriptor_version: str
    adapter_family: str
    implementation_ref: str
    implementation_version: str
    supported_contracts: list[dict[str, str]] = Field(min_length=1)
    supported_target_kinds: list[str]
    capabilities: list[CapabilityDeclaration]
    config_schema_ref: str
    descriptor_digest: str


class CapabilityRequirement(AdapterModel):
    capability_id: str
    version_range: str
    required: bool = True
    constraint_schema_ref: str | None = None
    typed_constraints: Any | None = None


class CapabilityResolution(AdapterModel):
    requirement_ref: str
    capability_id: str
    selected_version: str | None = None
    declaration_ref: str | None = None
    satisfied: bool
    mismatch_reason: str | None = None


class CapabilityEnvelope(AdapterModel):
    envelope_id: str
    principal_ref: str
    grantee_ref: str
    scope_ref: dict[str, str]
    allowed_capabilities: list[CapabilityResolution]
    data_scope: dict[str, Any]
    resource_scope: dict[str, Any]
    budget_limits: list[dict[str, Any]]
    allowed_side_effects: list[str]
    approval_refs: list[dict[str, Any]]
    policy_ref: dict[str, str]
    policy_version: int
    valid_from: str
    valid_until: str
    state: str = "active"
    issued_at: str = ""


class ExecutionBinding(AdapterModel):
    binding_id: str
    binding_scope: dict[str, Any]
    target_kind: str
    adapter_id: str
    descriptor_ref: dict[str, Any]
    descriptor_digest: str
    family_contract_id: str
    selected_contract_version: str
    required_capabilities: list[CapabilityRequirement]
    resolved_capabilities: list[CapabilityResolution]
    capability_envelope_ref: dict[str, Any]
    implementation_ref: str
    implementation_version: str
    selection_source_ref: dict[str, str]
    created_at: str


class AdapterRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[str, AdapterDescriptor] = {}

    def register(self, descriptor: AdapterDescriptor) -> None:
        body = descriptor.model_dump(exclude={"descriptor_digest"}, exclude_none=True)
        expected = sha256_digest(body)
        if descriptor.descriptor_digest != expected:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.adapter.descriptor-digest-mismatch",
                    category="validation",
                    message="Adapter descriptor digest does not match its content.",
                )
            )
        self._descriptors[descriptor.descriptor_id] = descriptor

    def descriptor(self, descriptor_id: str) -> AdapterDescriptor:
        try:
            return self._descriptors[descriptor_id]
        except KeyError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.adapter.unknown-descriptor",
                    category="incompatible",
                    message=f"Unknown adapter descriptor: {descriptor_id}.",
                )
            ) from exc

    def bind(
        self,
        *,
        descriptor_id: str,
        target_kind: str,
        required_capabilities: list[CapabilityRequirement],
        binding_id: str,
        scope_ref: dict[str, str],
        capability_envelope_ref: dict[str, Any],
        selection_source_ref: dict[str, str],
    ) -> ExecutionBinding:
        descriptor = self.descriptor(descriptor_id)
        if target_kind not in descriptor.supported_target_kinds:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.adapter.target-kind-unsupported",
                    category="incompatible",
                    message=f"Adapter does not support target kind {target_kind}.",
                )
            )
        capabilities = {cap.capability_id: cap for cap in descriptor.capabilities}
        resolutions: list[CapabilityResolution] = []
        for index, requirement in enumerate(required_capabilities):
            declaration = capabilities.get(requirement.capability_id)
            if declaration is None:
                if requirement.required:
                    raise ShadowDomainError(
                        ShadowError(
                            code="shadow.adapter.required-capability-unknown",
                            category="incompatible",
                            message=f"Required capability is not declared: {requirement.capability_id}.",
                        )
                    )
                resolutions.append(
                    CapabilityResolution(
                        requirement_ref=f"requirement-{index}",
                        capability_id=requirement.capability_id,
                        satisfied=False,
                        mismatch_reason="shadow.capability.missing",
                    )
                )
                continue
            resolutions.append(
                CapabilityResolution(
                    requirement_ref=f"requirement-{index}",
                    capability_id=requirement.capability_id,
                    selected_version=declaration.capability_version,
                    declaration_ref=f"{descriptor.descriptor_id}#{requirement.capability_id}",
                    satisfied=True,
                )
            )
        return ExecutionBinding(
            binding_id=binding_id,
            binding_scope={"scope_kind": "run", "scope_ref": scope_ref},
            target_kind=target_kind,
            adapter_id=descriptor.descriptor_id,
            descriptor_ref={"record_id": descriptor.descriptor_id, "version": 1},
            descriptor_digest=descriptor.descriptor_digest,
            family_contract_id=descriptor.adapter_family,
            selected_contract_version=descriptor.supported_contracts[0]["version_range"],
            required_capabilities=required_capabilities,
            resolved_capabilities=resolutions,
            capability_envelope_ref=capability_envelope_ref,
            implementation_ref=descriptor.implementation_ref,
            implementation_version=descriptor.implementation_version,
            selection_source_ref=selection_source_ref,
            created_at=utc_timestamp(),
        )
