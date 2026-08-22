from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from shadow_application.index import (
    MemoryIndexBuildArtifact,
    MemoryIndexEntry,
    MemoryIndexRebuildRequest,
    MemoryIndexRebuildResult,
    memory_index_artifact_digest,
    memory_index_entry_digest,
    memory_index_result_digest,
)
from shadow_application.recall import MemorySnapshot
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.models import StableRecordRef


@dataclass(slots=True)
class DeterministicMemoryIndexAdapter:
    """Stage-then-publish Index Adapter for Contract and local tests."""

    adapter_version: str = "0.1.0"
    result_state: Literal["complete", "unavailable"] = "complete"
    published: dict[str, MemoryIndexRebuildResult] = field(default_factory=dict, init=False)
    _staged: dict[str, MemoryIndexBuildArtifact] = field(default_factory=dict, init=False)
    _request_bindings: dict[str, tuple[str, str, str]] = field(default_factory=dict, init=False)

    def stage(
        self,
        request: MemoryIndexRebuildRequest,
        snapshots: list[MemorySnapshot],
        snapshot_digest: str,
    ) -> MemoryIndexBuildArtifact:
        if self.result_state == "unavailable":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.index-unavailable",
                    category="unavailable",
                    message="Deterministic Index Adapter is unavailable.",
                    retryable=True,
                )
            )
        binding = self._request_bindings.get(request.rebuild_request_id)
        requested_binding = (snapshot_digest, request.index_schema_ref, request.index_revision)
        if binding is not None and binding != requested_binding:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.index-replay-conflict",
                    category="conflict",
                    message="Rebuild request was reused with a different snapshot or revision.",
                    typed_details={
                        "rebuild_request_id": request.rebuild_request_id,
                        "prior_snapshot_digest": binding[0],
                        "requested_snapshot_digest": snapshot_digest,
                    },
                )
            )
        entries = [
            MemoryIndexEntry(
                record_ref=snapshot.record_ref,
                owner_ref=snapshot.owner_ref,
                space_id=snapshot.space_id,
                payload_digest=snapshot.payload_digest,
                index_revision=request.index_revision,
                derived_fields=self._derived_fields(snapshot),
            )
            for snapshot in snapshots
        ]
        entries.sort(key=lambda entry: (entry.record_ref.record_id, entry.record_ref.version))
        entry_digests = [memory_index_entry_digest(entry) for entry in entries]
        artifact = MemoryIndexBuildArtifact(
            snapshot_digest=snapshot_digest,
            index_schema_ref=request.index_schema_ref,
            index_revision=request.index_revision,
            entries=entries,
            entry_digests=entry_digests,
        )
        artifact.artifact_digest = memory_index_artifact_digest(artifact)
        self._staged[request.rebuild_request_id] = artifact
        return artifact

    def publish(
        self,
        request: MemoryIndexRebuildRequest,
        artifact: MemoryIndexBuildArtifact,
    ) -> MemoryIndexRebuildResult:
        prior = self.published.get(request.rebuild_request_id)
        if prior is not None:
            if (
                prior.snapshot_digest != artifact.snapshot_digest
                or prior.index_schema_ref != artifact.index_schema_ref
                or prior.index_revision != artifact.index_revision
            ):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.index-replay-conflict",
                        category="conflict",
                        message="Rebuild request was reused with a different snapshot or revision.",
                    )
                )
            return prior.model_copy(update={"replayed": True})
        if self.result_state == "unavailable":
            return MemoryIndexRebuildResult(
                result_state="unavailable",
                snapshot_digest=artifact.snapshot_digest,
                index_schema_ref=artifact.index_schema_ref,
                index_revision=artifact.index_revision,
                failure_detail={
                    "code": "shadow.memory.index-unavailable",
                    "adapter_version": self.adapter_version,
                },
            )
        snapshot_ref = StableRecordRef(
            record_id=f"memory-index-{sha256_digest({'snapshot_digest': artifact.snapshot_digest, 'index_schema_ref': artifact.index_schema_ref, 'index_revision': artifact.index_revision})[7:23]}"
        )
        result = MemoryIndexRebuildResult(
            result_state="complete",
            snapshot_digest=artifact.snapshot_digest,
            index_snapshot_ref=snapshot_ref,
            index_schema_ref=artifact.index_schema_ref,
            index_revision=artifact.index_revision,
            entry_count=len(artifact.entries),
            entry_digests=list(artifact.entry_digests),
            entries=list(artifact.entries),
            published=True,
        )
        result = result.model_copy(update={"result_digest": memory_index_result_digest(result)})
        self.published[request.rebuild_request_id] = result
        self._request_bindings[request.rebuild_request_id] = (
            artifact.snapshot_digest,
            artifact.index_schema_ref,
            artifact.index_revision,
        )
        self._staged.pop(request.rebuild_request_id, None)
        return result

    def discard(
        self, request: MemoryIndexRebuildRequest, artifact: MemoryIndexBuildArtifact
    ) -> None:
        staged = self._staged.get(request.rebuild_request_id)
        if staged is not None and staged.artifact_digest == artifact.artifact_digest:
            self._staged.pop(request.rebuild_request_id, None)
        published = self.published.get(request.rebuild_request_id)
        if published is not None and published.snapshot_digest == artifact.snapshot_digest:
            self.published.pop(request.rebuild_request_id, None)
            self._request_bindings.pop(request.rebuild_request_id, None)

    @staticmethod
    def _derived_fields(snapshot: MemorySnapshot) -> dict[str, str | None]:
        payload = snapshot.record["typed_payload"]
        scope = payload.get("applicability_scope") or {}
        return {
            "memory_kind": payload.get("memory_kind"),
            "scope_kind": scope.get("scope_kind"),
        }


__all__ = ["DeterministicMemoryIndexAdapter"]
