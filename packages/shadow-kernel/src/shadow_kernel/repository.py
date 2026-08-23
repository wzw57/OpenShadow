from __future__ import annotations

from typing import Any, Protocol

from .errors import RepositoryUnavailable
from .models import CommitBatchResult, CommitPlan


class CanonicalRepository(Protocol):
    """Minimal port implemented by a durable Store Adapter."""

    available: bool

    def set_available(self, available: bool) -> None: ...
    def health(self) -> dict[str, Any]: ...
    def current_version(self, record_id: str) -> int | None: ...
    def get(
        self, record_id: str, version: int | None = None, include_states: set[str] | None = None
    ) -> dict[str, Any] | None: ...
    def query(self, **kwargs: Any) -> list[dict[str, Any]]: ...
    def commit_batch(self, plan: CommitPlan) -> CommitBatchResult: ...
    def idempotency_result(self, idempotency_scope: str, idempotency_key: str) -> dict[str, Any] | None: ...


class EventStoreCapability(Protocol):
    """Optional durable Run event stream capability."""

    def append_event(
        self, run_id: str, event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...
    def events(self, run_id: str, after_sequence: int = 0) -> list[dict[str, Any]]: ...


class ErasureCapability(Protocol):
    """Optional irreversible-history capability."""

    def erase_history(self, record_id: str, keep_version: int) -> int: ...


class PortableTransferCapability(Protocol):
    """Optional export/import capability supplied by Store Adapters."""

    def export_records(self, **kwargs: Any) -> dict[str, Any]: ...

    def import_records(self, **kwargs: Any) -> dict[str, Any]: ...


class StoreFactory(Protocol):
    """Injectable Store construction boundary used by the Server composition root."""

    def __call__(self, database_url: str) -> CanonicalRepository: ...


__all__ = [
    "CanonicalRepository",
    "ErasureCapability",
    "EventStoreCapability",
    "PortableTransferCapability",
    "RepositoryUnavailable",
    "StoreFactory",
]
