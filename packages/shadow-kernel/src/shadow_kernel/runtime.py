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


def request_text(request: ExecutionRequest | str) -> str:
    """Compatibility helper for text-oriented adapters during migration."""
    if isinstance(request, str):
        return request
    typed_input = request.typed_input
    if isinstance(typed_input, str):
        return typed_input
    if isinstance(typed_input, dict) and isinstance(typed_input.get("text"), str):
        return typed_input["text"]
    return str(typed_input)


__all__ = ["RuntimeAdapter", "request_text"]
