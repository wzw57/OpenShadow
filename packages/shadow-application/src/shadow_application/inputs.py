from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from shadow_kernel.errors import ShadowDomainError, ShadowError


class ProposalCommandBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: str
    proposed_operation: str
    target_ref: dict[str, Any] | None = None
    expected_version: int | None = Field(default=None, ge=1)
    proposal_reason: str | None = None


class StateProposalCommand(ProposalCommandBase):
    input_type: str = "shadow.state-proposal"
    state_key: str
    value_schema_ref: str
    proposed_value: Any = None
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    observed_at: str
    expires_at: str
    source_status: str = "available"


class TaskProposalCommand(ProposalCommandBase):
    input_type: str = "shadow.durable-task-proposal"
    task_key: str
    goal: str
    completion_criteria: Any
    waiting_condition: Any | None = None
    deadline: str | None = None
    result_ref: dict[str, Any] | None = None
    failure_summary: Any | None = None


class ActionProposalCommand(ProposalCommandBase):
    input_type: str = "shadow.action-proposal"
    proposed_operation: str = "create"
    action_kind: str
    target_ref: dict[str, Any]
    typed_parameters: dict[str, Any]
    data_classification: str
    side_effect_level: str
    required_capabilities: list[str] = Field(default_factory=list)
    deadline: str
    secret_refs: list[str] = Field(default_factory=list)
    provider_target_kind: str | None = None


class ActionApprovalProposalCommand(ProposalCommandBase):
    input_type: str = "shadow.action-approval-proposal"
    action_ref: dict[str, Any]
    expected_version: int = Field(ge=1)
    approver_ref: str
    decision: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)


ProposalCommand = (
    StateProposalCommand
    | TaskProposalCommand
    | ActionProposalCommand
    | ActionApprovalProposalCommand
)


class _StateProposalHandler:
    def __init__(self, service: Any) -> None:
        self.service = service

    def submit(self, command: StateProposalCommand, *, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        target_state_id = command.target_ref.get("record_id") if command.target_ref else None
        candidate = self.service.propose(
            submitted_by=principal_ref,
            owner_ref=principal_ref,
            space_id=space_id,
            operation=command.proposed_operation,
            state_key=command.state_key,
            value_schema_ref=command.value_schema_ref,
            proposed_value=command.proposed_value,
            evidence_refs=command.evidence_refs,
            source_refs=command.source_refs,
            observed_at=command.observed_at,
            expires_at=command.expires_at,
            source_status=command.source_status,
            target_state_id=target_state_id,
            expected_version=command.expected_version,
            proposal_reason=command.proposal_reason,
        )
        return {"record": self.service.submit_proposal(candidate, idempotency_key=idempotency_key)}

    def accept(self, *, proposal_id: str, expected_version: int, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return self.service.accept_proposal(
            proposal_id=proposal_id,
            proposal_expected_version=expected_version,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )


class _TaskProposalHandler:
    def __init__(self, service: Any) -> None:
        self.service = service

    def submit(self, command: TaskProposalCommand, *, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        target_task_id = command.target_ref.get("record_id") if command.target_ref else None
        candidate = self.service.propose(
            submitted_by=principal_ref,
            owner_ref=principal_ref,
            space_id=space_id,
            operation=command.proposed_operation,
            task_key=command.task_key,
            goal=command.goal,
            completion_criteria=command.completion_criteria,
            target_task_id=target_task_id,
            expected_version=command.expected_version,
            waiting_condition=command.waiting_condition,
            deadline=command.deadline,
            result_ref=command.result_ref,
            failure_summary=command.failure_summary,
            proposal_reason=command.proposal_reason,
        )
        return {"record": self.service.submit_proposal(candidate, idempotency_key=idempotency_key)}

    def accept(self, *, proposal_id: str, expected_version: int, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return self.service.accept_proposal(
            proposal_id=proposal_id,
            proposal_expected_version=expected_version,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )


class _ActionProposalHandler:
    def __init__(self, service: Any) -> None:
        self.service = service

    def submit(self, command: ActionProposalCommand | ActionApprovalProposalCommand, *, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        if isinstance(command, ActionApprovalProposalCommand):
            action_id = command.action_ref.get("record_id")
            if not action_id:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.action.approval-target-missing",
                        category="validation",
                        message="Action approval requires action_ref.record_id.",
                    )
                )
            candidate = self.service.propose_approval(
                submitted_by=principal_ref,
                owner_ref=principal_ref,
                space_id=space_id,
                action_id=action_id,
                expected_version=command.expected_version,
                approver_ref=command.approver_ref,
                decision=command.decision,
                evidence_refs=command.evidence_refs,
                proposal_reason=command.proposal_reason,
            )
        else:
            candidate = self.service.propose_action(
                submitted_by=principal_ref,
                owner_ref=principal_ref,
                space_id=space_id,
                action_kind=command.action_kind,
                target_ref=command.target_ref,
                typed_parameters=command.typed_parameters,
                data_classification=command.data_classification,
                side_effect_level=command.side_effect_level,
                required_capabilities=command.required_capabilities,
                deadline=command.deadline,
                secret_refs=command.secret_refs,
                provider_target_kind=command.provider_target_kind,
                proposal_reason=command.proposal_reason,
            )
        return {"record": self.service.submit_proposal(candidate, idempotency_key=idempotency_key)}

    def accept(self, *, proposal_id: str, expected_version: int, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return self.service.accept_proposal(
            proposal_id=proposal_id,
            proposal_expected_version=expected_version,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )


class ProposalHandlerRegistry:
    """Namespaced proposal dispatch; generic Server never branches on Profile classes."""

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}

    @classmethod
    def from_services(cls, *, states: Any, tasks: Any, actions: Any) -> ProposalHandlerRegistry:
        registry = cls()
        registry.register("shadow.state-proposal", _StateProposalHandler(states))
        registry.register("shadow.durable-task-proposal", _TaskProposalHandler(tasks))
        action_handler = _ActionProposalHandler(actions)
        registry.register("shadow.action-proposal", action_handler)
        registry.register("shadow.action-approval-proposal", action_handler)
        return registry

    def register(self, input_type: str, handler: Any) -> None:
        if input_type in self._handlers:
            raise ValueError(f"Proposal input type already registered: {input_type}")
        self._handlers[input_type] = handler

    def handler_for(self, input_type: str) -> Any:
        try:
            return self._handlers[input_type]
        except KeyError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.proposal.input-unsupported",
                    category="unsupported",
                    message=f"No proposal handler is registered for {input_type}.",
                )
            ) from exc

    def submit(self, command: ProposalCommand, *, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return self.handler_for(command.input_type).submit(
            command,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )

    def accept(self, proposal_type: str, *, proposal_id: str, expected_version: int, principal_ref: str, space_id: str, idempotency_key: str) -> dict[str, Any]:
        return self.handler_for(proposal_type).accept(
            proposal_id=proposal_id,
            expected_version=expected_version,
            principal_ref=principal_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )

    def input_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


__all__ = [
    "ActionApprovalProposalCommand",
    "ActionProposalCommand",
    "ProposalCommand",
    "ProposalHandlerRegistry",
    "StateProposalCommand",
    "TaskProposalCommand",
]
