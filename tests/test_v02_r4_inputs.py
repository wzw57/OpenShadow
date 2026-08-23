from __future__ import annotations

from typing import Any

import pytest
from shadow_application import ProposalHandlerRegistry
from shadow_kernel.errors import ShadowDomainError


class _ExampleHandler:
    def submit(self, command: Any, *, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return {
            "record": {
                "record_type": "shadow.profile.example",
                "typed_payload": command,
                "owner_ref": principal_ref,
                "space_id": space_id,
                "idempotency_key": idempotency_key,
            }
        }

    def accept(self, **kwargs: Any) -> dict[str, Any]:
        return {"accepted": kwargs["proposal_id"]}


def test_builtin_proposal_registry_has_namespaced_handlers() -> None:
    from pathlib import Path

    from shadow_application import ActionService, StateService, TaskService
    from shadow_kernel.commit import CommitAuthority
    from shadow_kernel.registry import ContractRegistry
    from shadow_store import SqliteCanonicalRepository

    root = Path(__file__).resolve().parents[1]
    repository = SqliteCanonicalRepository("sqlite://")
    authority = CommitAuthority(repository, ContractRegistry(root))
    registry = ProposalHandlerRegistry.from_services(
        states=StateService(repository, authority, ContractRegistry(root)),
        tasks=TaskService(repository, authority, ContractRegistry(root)),
        actions=ActionService(repository, authority, ContractRegistry(root)),
    )
    assert registry.input_types() == (
        "shadow.action-approval-proposal",
        "shadow.action-proposal",
        "shadow.durable-task-proposal",
        "shadow.state-proposal",
    )


def test_example_input_can_register_without_server_branch() -> None:
    registry = ProposalHandlerRegistry()
    registry.register("example.profile.create", _ExampleHandler())
    result = registry.submit(
        type("ExampleCommand", (), {"input_type": "example.profile.create"})(),
        principal_ref="owner-example",
        space_id="space-example",
        idempotency_key="example-1",
    )
    assert result["record"]["record_type"] == "shadow.profile.example"

    with pytest.raises(ShadowDomainError) as unsupported:
        registry.handler_for("example.missing")
    assert unsupported.value.error.code == "shadow.proposal.input-unsupported"
