from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from shadow_kernel.commit import CommitAuthority
from shadow_kernel.dispatch import DispatchResult, ExecutionDispatcher
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.models import CommitBatchResult, CommitPlan, ExecutionRequest
from shadow_kernel.repository import CanonicalRepository


@dataclass(frozen=True, slots=True)
class DurableFinalization:
    plan: CommitPlan
    event_type: str
    event_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DurableExecutionResult:
    initial_commit: CommitBatchResult
    final_commit: CommitBatchResult | None
    dispatch: DispatchResult | None
    failure: dict[str, Any] | None = None
    replayed: bool = False


class ExecutionCoordinator:
    """Application seam for the durable execution boundary.

    R3 first centralizes the typed dispatch and policy checks here.  The
    surrounding Conversation facade still owns its legacy record extraction;
    subsequent slices move Admission/Run/Attempt preparation behind this seam.
    """

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        dispatcher: ExecutionDispatcher,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.dispatcher = dispatcher

    def execute(
        self,
        request: ExecutionRequest,
        *,
        target_kind: str,
        required_capabilities: list[str] | None = None,
        idempotency_scope: str = "execution",
    ) -> DispatchResult:
        return self.dispatcher.dispatch(
            request,
            target_kind=target_kind,
            required_capabilities=required_capabilities,
            idempotency_scope=idempotency_scope,
        )

    def execute_durable(
        self,
        *,
        initial_plan: CommitPlan,
        request: ExecutionRequest,
        target_kind: str,
        run_id: str,
        attempt_id: str,
        finalize: Callable[[DispatchResult | None, dict[str, Any] | None], DurableFinalization],
        required_capabilities: list[str] | None = None,
        idempotency_scope: str = "execution",
    ) -> DurableExecutionResult:
        """Own the durable boundary around provider invocation.

        Profile code supplies only the typed finalization builder.  Initial
        durable records, the started event, provider call, final CAS commit and
        terminal event are sequenced here.
        """
        initial_commit = self.authority.commit(initial_plan)
        if initial_commit.outcome == "failed":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.initial-commit-failed",
                    category="unavailable",
                    message="Durable execution records could not be committed.",
                    retryable=True,
                    typed_details=initial_commit.structured_error,
                )
            )
        if initial_commit.outcome == "idempotent_replay":
            return DurableExecutionResult(
                initial_commit=initial_commit,
                final_commit=None,
                dispatch=None,
                replayed=True,
            )
        self.repository.append_event(
            run_id,
            "shadow.run.started",
            {"run_id": run_id, "attempt_id": attempt_id},
        )
        dispatch: DispatchResult | None = None
        failure: dict[str, Any] | None = None
        try:
            dispatch = self.execute(
                request,
                target_kind=target_kind,
                required_capabilities=required_capabilities,
                idempotency_scope=idempotency_scope,
            )
        except Exception as exc:  # Provider failures become durable unknown outcomes.
            failure = {"code": "shadow.runtime.outcome-unknown", "reason": str(exc)[:500]}
        finalization = finalize(dispatch, failure)
        final_commit = self.authority.commit(finalization.plan)
        if final_commit.outcome in {"failed", "conflict"}:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.execution.result-commit-failed",
                    category="conflict" if final_commit.outcome == "conflict" else "unavailable",
                    message="Runtime result could not be durably committed.",
                    retryable=final_commit.outcome == "failed",
                    typed_details=final_commit.structured_error,
                )
            )
        self.repository.append_event(run_id, finalization.event_type, finalization.event_payload)
        return DurableExecutionResult(
            initial_commit=initial_commit,
            final_commit=final_commit,
            dispatch=dispatch,
            failure=failure,
        )


__all__ = ["DurableExecutionResult", "DurableFinalization", "ExecutionCoordinator"]
