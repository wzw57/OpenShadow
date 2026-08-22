from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from shadow_kernel.registry import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ContractRegistry(ROOT)


FIXTURE_SCHEMA_REFS = {
    "canonical/valid-envelope.json": "kernel#/$defs/CanonicalEnvelope",
    "canonical/invalid-envelope.json": "kernel#/$defs/CanonicalEnvelope",
    "canonical/invalid-tombstone-envelope.json": "kernel#/$defs/CanonicalEnvelope",
    "canonical/valid-tombstone-envelope.json": "kernel#/$defs/CanonicalEnvelope",
    "kernel/invalid-accepted-admission.json": "kernel#/$defs/AdmissionRecordPayload",
    "kernel/valid-accepted-admission.json": "kernel#/$defs/AdmissionRecordPayload",
    "kernel/invalid-rejected-decision-version.json": "kernel#/$defs/CommitDecision",
    "kernel/valid-accepted-decision.json": "kernel#/$defs/CommitDecision",
    "adapters/invalid-capability.json": "adapters#/$defs/AdapterDescriptor",
    "adapters/invalid-unsatisfied-allowed-capability.json": "adapters#/$defs/CapabilityEnvelopePayload",
    "adapters/valid-adapter.json": "adapters#/$defs/AdapterDescriptor",
    "adapters/valid-capability-envelope.json": "adapters#/$defs/CapabilityEnvelopePayload",
    "profiles/invalid-memory-merge-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/invalid-memory-correction-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/invalid-memory-invalidate-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/invalid-memory.json": "profiles#/$defs/MemoryPayload",
    "profiles/invalid-message.json": "profiles#/$defs/MessagePayload",
    "profiles/valid-conversation.json": "profiles#/$defs/ConversationPayload",
    "profiles/valid-memory-correction-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/valid-memory-invalidate-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/valid-memory-merge-proposal.json": "profiles#/$defs/MemoryProposalPayload",
    "profiles/valid-memory.json": "profiles#/$defs/MemoryPayload",
    "repository/invalid-commit-plan.json": "repository#/$defs/CommitPlan",
    "repository/invalid-failed-result-metadata.json": "repository#/$defs/CommitBatchResult",
    "repository/valid-commit-plan.json": "repository#/$defs/CommitPlan",
    "repository/valid-committed-result.json": "repository#/$defs/CommitBatchResult",
    "state/invalid-state.json": "state#/$defs/StatePayload",
    "state/invalid-state-proposal.json": "state#/$defs/StateProposalPayload",
    "state/valid-observation-source-unavailable.json": "state#/$defs/Observation",
    "state/valid-state-proposal.json": "state#/$defs/StateProposalPayload",
    "state/valid-state.json": "state#/$defs/StatePayload",
    "continuity/invalid-task.json": "continuity#/$defs/TaskPayload",
    "continuity/valid-checkpoint.json": "continuity#/$defs/CheckpointPayload",
    "continuity/valid-task-proposal.json": "continuity#/$defs/TaskProposalPayload",
    "continuity/valid-task.json": "continuity#/$defs/TaskPayload",
    "continuity/valid-trigger-observation.json": "continuity#/$defs/TriggerObservation",
    "action/invalid-approval-decision.json": "action#/$defs/ApprovalProposalPayload",
    "action/invalid-inline-secret.json": "action#/$defs/ActionProposalPayload",
    "action/valid-action.json": "action#/$defs/ActionPayload",
    "action/valid-action-proposal.json": "action#/$defs/ActionProposalPayload",
    "action/valid-approval-proposal.json": "action#/$defs/ApprovalProposalPayload",
    "action/valid-provider-result.json": "action#/$defs/ProviderResultPayload",
    "action/valid-reconciliation.json": "action#/$defs/ReconciliationPayload",
}


def _schema_ref(short_ref: str) -> str:
    family, fragment = short_ref.split("#", 1)
    return f"https://schemas.openshadow.dev/contracts/{family}/1.0.0#{fragment}"


@pytest.mark.parametrize("relative_path", sorted(FIXTURE_SCHEMA_REFS))
def test_declared_fixture_is_checked_against_offline_contract(relative_path: str) -> None:
    fixture = json.loads(
        (ROOT / "contracts" / "fixtures" / relative_path).read_text(encoding="utf-8")
    )
    schema_ref = _schema_ref(FIXTURE_SCHEMA_REFS[relative_path])
    should_be_valid = not relative_path.startswith(
        (
            "canonical/invalid",
            "adapters/invalid",
            "kernel/invalid",
            "profiles/invalid",
            "state/invalid",
            "continuity/invalid",
            "action/invalid",
            "repository/invalid",
        )
    )
    if should_be_valid:
        REGISTRY.validate(fixture, schema_ref)
    else:
        with pytest.raises(ValidationError):
            REGISTRY.validate(fixture, schema_ref)
