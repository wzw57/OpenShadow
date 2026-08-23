from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from .models import ExecutionRequest


class RuntimeAdapter(Protocol):
    """Typed Runtime Adapter port; optional capabilities stay negotiated."""

    target_kind: str

    def describe(self) -> dict[str, Any]: ...
    def execute(self, request: ExecutionRequest) -> Any: ...
    def events(self, execution_ref: str, after_cursor: str | None = None) -> Iterable[dict[str, Any]]: ...

__all__ = ["RuntimeAdapter"]
