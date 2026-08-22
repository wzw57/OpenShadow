from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from shadow_application.recall import (
    MemoryMaintenanceRequest,
    MemoryMaintenanceResult,
    MemoryRecallItem,
    MemoryRecallQuery,
    MemoryRecallResult,
    MemorySnapshot,
)
from shadow_kernel.models import StableRecordRef


@dataclass(frozen=True, slots=True)
class DeterministicMemoryRecallAdapter:
    """Small text-match Recall Adapter used for Contract and local tests."""

    adapter_version: str = "0.1.0"
    result_state: Literal["complete", "stale", "unavailable"] = "complete"
    index_snapshot_ref: StableRecordRef = field(
        default_factory=lambda: StableRecordRef(record_id="memory-index-deterministic-v1")
    )

    def recall(
        self, query: MemoryRecallQuery, snapshots: list[MemorySnapshot]
    ) -> MemoryRecallResult:
        if self.result_state != "complete":
            return MemoryRecallResult(
                result_state=self.result_state,
                index_snapshot_ref=self.index_snapshot_ref,
            )
        query_tokens = {token for token in (query.query_text or "").lower().split() if token}
        ranked: list[tuple[float, MemorySnapshot]] = []
        for snapshot in snapshots:
            content = snapshot.record["typed_payload"].get("typed_content")
            haystack = str(content).lower()
            if not query_tokens:
                score = 1.0
            else:
                matched = sum(token in haystack for token in query_tokens)
                score = matched / len(query_tokens)
            if score > 0:
                ranked.append((score, snapshot))
        ranked.sort(key=lambda item: (-item[0], item[1].record_ref.record_id))
        result_state: Literal["complete", "stale"] = (
            "stale" if any(not snapshot.is_current_head for _, snapshot in ranked) else "complete"
        )
        return MemoryRecallResult(
            result_state=result_state,
            items=[
                MemoryRecallItem(
                    record_ref=snapshot.record_ref,
                    match_kind="deterministic-text",
                    score=score,
                    index_snapshot_ref=self.index_snapshot_ref,
                )
                for score, snapshot in ranked[: query.limit]
            ],
            index_snapshot_ref=self.index_snapshot_ref,
        )


@dataclass(frozen=True, slots=True)
class DeterministicMemoryMaintenanceAdapter:
    """Configurable Maintenance Adapter for proposal boundary tests."""

    proposals: tuple[dict, ...] = ()
    adapter_version: str = "0.1.0"
    result_state: Literal["complete", "partial", "unavailable"] = "complete"

    def maintain(
        self,
        request: MemoryMaintenanceRequest,
        snapshots: list[MemorySnapshot],
    ) -> MemoryMaintenanceResult:
        del request, snapshots
        return MemoryMaintenanceResult(
            result_state=self.result_state,
            proposals=list(self.proposals) if self.result_state != "unavailable" else [],
            adapter_version=self.adapter_version,
        )


__all__ = [
    "DeterministicMemoryMaintenanceAdapter",
    "DeterministicMemoryRecallAdapter",
]
