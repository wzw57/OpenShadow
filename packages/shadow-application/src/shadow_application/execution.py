from __future__ import annotations

from shadow_kernel.dispatch import DispatchResult, ExecutionDispatcher
from shadow_kernel.models import ExecutionRequest


class ExecutionCoordinator:
    """Application seam for the durable execution boundary.

    R3 first centralizes the typed dispatch and policy checks here.  The
    surrounding Conversation facade still owns its legacy record extraction;
    subsequent slices move Admission/Run/Attempt preparation behind this seam.
    """

    def __init__(self, dispatcher: ExecutionDispatcher) -> None:
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


__all__ = ["ExecutionCoordinator"]
