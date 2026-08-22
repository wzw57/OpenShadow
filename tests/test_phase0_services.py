from __future__ import annotations

from pathlib import Path

import pytest
from shadow_application import MemoryService
from shadow_kernel.adapters import AdapterDescriptor, AdapterRegistry, CapabilityRequirement
from shadow_kernel.admission import AdmissionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]


def test_adapter_binding_rejects_unknown_target_and_required_capability() -> None:
    body = {
        "descriptor_id": "adapter-test",
        "descriptor_version": "1.0.0",
        "adapter_family": "shadow.execution",
        "implementation_ref": "test://adapter",
        "implementation_version": "1.0.0",
        "supported_contracts": [{"contract_id": "shadow.execution", "version_range": "1.0.0"}],
        "supported_target_kinds": ["shadow.test-runner"],
        "capabilities": [
            {
                "capability_id": "shadow.execution.cancel",
                "capability_version": "1.0.0",
                "contract_ref": "https://schemas.openshadow.dev/contracts/execution/1.0.0",
            }
        ],
        "config_schema_ref": "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor",
    }
    registry = AdapterRegistry()
    registry.register(AdapterDescriptor(**body, descriptor_digest=sha256_digest(body)))

    with pytest.raises(ShadowDomainError) as unknown_target:
        registry.bind(
            descriptor_id="adapter-test",
            target_kind="shadow.other-runner",
            required_capabilities=[],
            binding_id="binding-1",
            scope_ref={"record_id": "run-1"},
            capability_envelope_ref={"record_id": "cap-1", "version": 1},
            selection_source_ref={"record_id": "request-1"},
        )
    assert unknown_target.value.error.code == "shadow.adapter.target-kind-unsupported"

    with pytest.raises(ShadowDomainError) as missing_capability:
        registry.bind(
            descriptor_id="adapter-test",
            target_kind="shadow.test-runner",
            required_capabilities=[
                CapabilityRequirement(
                    capability_id="shadow.execution.checkpoint", version_range="1.0.0"
                )
            ],
            binding_id="binding-1",
            scope_ref={"record_id": "run-1"},
            capability_envelope_ref={"record_id": "cap-1", "version": 1},
            selection_source_ref={"record_id": "request-1"},
        )
    assert missing_capability.value.error.code == "shadow.adapter.required-capability-unknown"

    with pytest.raises(ShadowDomainError) as incompatible_version:
        registry.bind(
            descriptor_id="adapter-test",
            target_kind="shadow.test-runner",
            required_capabilities=[
                CapabilityRequirement(capability_id="shadow.execution.cancel", version_range="2.0.0")
            ],
            binding_id="binding-1",
            scope_ref={"record_id": "run-1"},
            capability_envelope_ref={"record_id": "cap-1", "version": 1},
            selection_source_ref={"record_id": "request-1"},
        )
    assert incompatible_version.value.error.code == "shadow.adapter.capability-version-incompatible"


def test_admission_is_atomic_and_degrades_explicitly(tmp_path: Path) -> None:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    authority = CommitAuthority(repository, ContractRegistry(ROOT))
    admission = AdmissionService(repository, authority)
    accepted = admission.admit(
        request_type="shadow.request.test",
        input_type="shadow.input.test",
        work_input={
            "schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_input": {"text": "durable input"},
        },
        principal_ref="principal-test",
        endpoint_ref="endpoint-test",
        space_id="space-test",
        idempotency_key="admission-1",
    )
    assert accepted.decision == "accepted"
    assert accepted.admission and accepted.request and accepted.requirements and accepted.run
    assert accepted.run["typed_payload"]["lifecycle"] == "queued"
    assert repository.current_version(accepted.admission["record_id"]) == 1
    assert repository.current_version(accepted.request["record_id"]) == 1

    repository.set_available(False)
    ephemeral = admission.admit(
        request_type="shadow.request.test",
        input_type="shadow.input.test",
        work_input={
            "schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_input": {"text": "not durable"},
        },
        principal_ref="principal-test",
        endpoint_ref="endpoint-test",
        space_id="space-test",
        idempotency_key="admission-2",
    )
    assert ephemeral.decision == "ephemeral"
    assert ephemeral.ephemeral and ephemeral.ephemeral.durable is False


def test_memory_candidate_requires_commit(tmp_path: Path) -> None:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    memories = MemoryService(repository, authority, registry)
    candidate = memories.propose_create(
        submitted_by="principal-test",
        owner_ref="principal-test",
        space_id="space-test",
        memory_kind="shadow.memory.preference",
        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
        typed_content={"text": "concise updates"},
        applicability_scope={"scope_kind": "shadow.scope.personal", "scope_refs": []},
    )
    assert repository.get(candidate.candidate_id) is None
    record = memories.commit_candidate(candidate, idempotency_key="memory-1")
    assert record["record_type"] == "shadow.profile.memory"
    assert record["typed_payload"]["created_from_ref"]["record_id"] == candidate.candidate_id


def test_commit_maps_schema_failure_to_structured_domain_error(tmp_path: Path) -> None:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    authority = CommitAuthority(repository, ContractRegistry(ROOT))
    operation = CommitOperation(
        operation_id="operation-invalid",
        operation="create",
        record_id="memory-invalid",
        record_type="shadow.profile.memory",
        target_schema_ref="https://schemas.openshadow.dev/contracts/profiles/1.0.0#/$defs/MemoryPayload",
        owner_ref="principal-test",
        space_id="space-test",
        created_by="principal-test",
        data_classification="personal",
        provenance=Provenance(origin_type="shadow.origin.test", origin_ref="test"),
        retention_policy_ref=StableRecordRef(record_id="retention-default"),
        typed_payload={"memory_kind": "not-namespaced"},
    )
    plan = CommitPlan(
        commit_request_id="commit-invalid",
        idempotency_scope="test",
        idempotency_key="invalid",
        request_digest=sha256_digest(operation.model_dump(mode="json")),
        actor_ref="principal-test",
        operations=[operation],
        prepared_at="2026-01-01T00:00:00Z",
    )
    with pytest.raises(ShadowDomainError) as failure:
        authority.commit(plan)
    assert failure.value.error.code == "shadow.contract.validation-failed"
    assert failure.value.error.category == "validation"
