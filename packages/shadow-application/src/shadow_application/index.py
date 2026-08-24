from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import Field, ValidationError, model_validator
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import RecordVersionRef, StableRecordRef, StrictModel
from shadow_kernel.repository import CanonicalRepository

from .recall import MemorySnapshot


class MemoryIndexRebuildRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    rebuild_request_id: str = Field(min_length=1, max_length=255)
    index_revision: str = Field(min_length=1, max_length=100)
    index_schema_ref: str = Field(min_length=1, max_length=1000)
    expected_snapshot_digest: str | None = Field(default=None, min_length=1, max_length=255)
    consistency: Literal["canonical"] = "canonical"
    max_entries: int = Field(default=10_000, ge=1, le=100_000)


class MemoryIndexEntry(StrictModel):
    record_ref: RecordVersionRef
    owner_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    payload_digest: str = Field(min_length=1, max_length=255)
    index_revision: str = Field(min_length=1, max_length=100)
    derived_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_canonical_content(self) -> MemoryIndexEntry:
        forbidden = {
            "record",
            "typed_content",
            "raw_content",
            "sensitive_content",
            "proposed_content",
        }

        def contains_forbidden(value: Any) -> bool:
            if isinstance(value, dict):
                return any(
                    key in forbidden or contains_forbidden(nested)
                    for key, nested in value.items()
                )
            if isinstance(value, list):
                return any(contains_forbidden(nested) for nested in value)
            return False

        if contains_forbidden(self.derived_fields):
            raise ValueError("Index entries cannot contain Canonical or sensitive content")
        return self


class MemoryIndexBuildArtifact(StrictModel):
    snapshot_digest: str = Field(min_length=1, max_length=255)
    index_schema_ref: str = Field(min_length=1, max_length=1000)
    index_revision: str = Field(min_length=1, max_length=100)
    entries: list[MemoryIndexEntry] = Field(default_factory=list, max_length=100_000)
    entry_digests: list[str] = Field(default_factory=list, max_length=100_000)
    artifact_digest: str = ""


class MemoryIndexRebuildResult(StrictModel):
    result_state: Literal["complete", "stale", "unavailable"]
    snapshot_digest: str = Field(min_length=1, max_length=255)
    index_snapshot_ref: StableRecordRef | None = None
    index_schema_ref: str = Field(min_length=1, max_length=1000)
    index_revision: str = Field(min_length=1, max_length=100)
    entry_count: int = Field(default=0, ge=0, le=100_000)
    entry_digests: list[str] = Field(default_factory=list, max_length=100_000)
    entries: list[MemoryIndexEntry] = Field(default_factory=list, max_length=100_000)
    result_digest: str = ""
    published: bool = False
    replayed: bool = False
    generated_at: str = Field(default_factory=utc_timestamp)
    failure_detail: dict[str, Any] | None = None


class MemoryIndexAdapter(Protocol):
    adapter_version: str

    def stage(
        self,
        request: MemoryIndexRebuildRequest,
        snapshots: list[MemorySnapshot],
        snapshot_digest: str,
    ) -> MemoryIndexBuildArtifact: ...

    def publish(
        self,
        request: MemoryIndexRebuildRequest,
        artifact: MemoryIndexBuildArtifact,
    ) -> MemoryIndexRebuildResult: ...

    def discard(
        self, request: MemoryIndexRebuildRequest, artifact: MemoryIndexBuildArtifact
    ) -> None: ...


def memory_index_snapshot_digest(
    principal_ref: str, space_id: str, snapshots: list[MemorySnapshot]
) -> str:
    ordered = sorted(
        snapshots, key=lambda snapshot: (snapshot.record_ref.record_id, snapshot.record_ref.version)
    )
    return sha256_digest(
        {
            "principal_ref": principal_ref,
            "space_id": space_id,
            "records": [
                {
                    "record_ref": snapshot.record_ref.model_dump(mode="json"),
                    "payload_digest": snapshot.payload_digest,
                }
                for snapshot in ordered
            ],
        }
    )


def memory_index_entry_digest(entry: MemoryIndexEntry) -> str:
    return sha256_digest(entry.model_dump(mode="json"))


def memory_index_artifact_digest(artifact: MemoryIndexBuildArtifact) -> str:
    return sha256_digest(
        {
            "snapshot_digest": artifact.snapshot_digest,
            "index_schema_ref": artifact.index_schema_ref,
            "index_revision": artifact.index_revision,
            "entry_digests": artifact.entry_digests,
        }
    )


def memory_index_result_digest(result: MemoryIndexRebuildResult) -> str:
    return sha256_digest(
        {
            "result_state": result.result_state,
            "snapshot_digest": result.snapshot_digest,
            "index_snapshot_ref": result.index_snapshot_ref.model_dump(mode="json")
            if result.index_snapshot_ref
            else None,
            "index_schema_ref": result.index_schema_ref,
            "index_revision": result.index_revision,
            "entry_count": result.entry_count,
            "entry_digests": result.entry_digests,
            "published": result.published,
            "failure_detail": result.failure_detail,
        }
    )


class MemoryIndexRebuildService:
    """Build and publish a derived index without granting it Canonical authority."""

    def __init__(self, repository: CanonicalRepository, adapter: MemoryIndexAdapter) -> None:
        self.repository = repository
        self.adapter = adapter

    def rebuild(self, request: MemoryIndexRebuildRequest) -> MemoryIndexRebuildResult:
        request = MemoryIndexRebuildRequest.model_validate(request)
        snapshots = self._active_snapshots(request.principal_ref, request.space_id)
        snapshot_digest = memory_index_snapshot_digest(
            request.principal_ref, request.space_id, snapshots
        )
        if (
            request.expected_snapshot_digest is not None
            and request.expected_snapshot_digest != snapshot_digest
        ):
            return self._stale_result(
                request,
                snapshot_digest,
                expected_snapshot_digest=request.expected_snapshot_digest,
            )
        try:
            staged = self.adapter.stage(request, snapshots, snapshot_digest)
            artifact = MemoryIndexBuildArtifact.model_validate(
                staged.model_dump(mode="json") if isinstance(staged, MemoryIndexBuildArtifact) else staged
            )
        except ValidationError as exc:
            raise self._invalid_error("Index staging artifact does not satisfy its Contract.") from exc
        except ShadowDomainError:
            raise
        except Exception as exc:
            raise self._unavailable_error("Index Adapter failed during staging.") from exc
        try:
            self._validate_artifact(artifact, request, snapshots, snapshot_digest)
        except Exception:
            self._discard(request, artifact)
            raise

        try:
            current_snapshots = self._active_snapshots(request.principal_ref, request.space_id)
        except Exception:
            self._discard(request, artifact)
            raise
        current_digest = memory_index_snapshot_digest(
            request.principal_ref, request.space_id, current_snapshots
        )
        if current_digest != snapshot_digest:
            self._discard(request, artifact)
            return self._stale_result(
                request,
                snapshot_digest,
                current_snapshot_digest=current_digest,
            )
        try:
            published = self.adapter.publish(request, artifact)
            result = MemoryIndexRebuildResult.model_validate(
                published.model_dump(mode="json")
                if isinstance(published, MemoryIndexRebuildResult)
                else published
            )
        except ValidationError as exc:
            self._discard(request, artifact)
            raise self._invalid_error("Index rebuild result does not satisfy its Contract.") from exc
        except ShadowDomainError:
            raise
        except Exception as exc:
            self._discard(request, artifact)
            raise self._unavailable_error("Index Adapter failed during publish.") from exc
        try:
            self._validate_result(result, request, artifact)
        except Exception:
            self._discard(request, artifact)
            raise
        result_digest = memory_index_result_digest(result)
        if result.result_digest and result.result_digest != result_digest:
            raise self._invalid_error("Index result digest does not match its result content.")
        return result.model_copy(update={"result_digest": result_digest})

    def _active_snapshots(self, owner_ref: str, space_id: str) -> list[MemorySnapshot]:
        if not self.repository.available:
            raise self._unavailable_error("Canonical Repository is unavailable for Index rebuild.")
        try:
            records = self.repository.query_heads(
                owner_refs={owner_ref},
                space_ids={space_id},
                record_types={"shadow.profile.memory"},
                record_states={"active", "logically_deleted", "erased"},
                limit=None,
            )
        except ShadowDomainError as exc:
            if exc.error.category == "unavailable":
                raise self._unavailable_error(
                    "Canonical Repository is unavailable for Index rebuild."
                ) from exc
            raise
        heads: dict[str, dict[str, Any]] = {}
        for record in records:
            previous = heads.get(record["record_id"])
            if previous is None or record["version"] > previous["version"]:
                heads[record["record_id"]] = record
        snapshots: list[MemorySnapshot] = []
        for record in sorted(heads.values(), key=lambda item: (item["record_id"], item["version"])):
            if (
                record["record_state"] != "active"
                or record["typed_payload"].get("memory_state") != "active"
            ):
                continue
            ref = RecordVersionRef(record_id=record["record_id"], version=record["version"])
            snapshots.append(
                MemorySnapshot(
                    record_ref=ref,
                    owner_ref=record["owner_ref"],
                    space_id=record["space_id"],
                    payload_digest=sha256_digest(
                        {
                            "record_ref": ref.model_dump(mode="json"),
                            "typed_payload": record["typed_payload"],
                        }
                    ),
                    record=record,
                )
            )
        return snapshots

    def _validate_artifact(
        self,
        artifact: MemoryIndexBuildArtifact,
        request: MemoryIndexRebuildRequest,
        snapshots: list[MemorySnapshot],
        snapshot_digest: str,
    ) -> None:
        if artifact.snapshot_digest != snapshot_digest:
            raise self._invalid_error("Index staging artifact snapshot digest is incorrect.")
        if artifact.index_revision != request.index_revision:
            raise self._invalid_error("Index staging artifact revision is incorrect.")
        if artifact.index_schema_ref != request.index_schema_ref:
            raise self._invalid_error("Index staging artifact schema is incorrect.")
        if len(artifact.entries) > request.max_entries:
            raise self._invalid_error("Index Adapter exceeded the requested entry limit.")
        allowed = {
            (snapshot.record_ref.record_id, snapshot.record_ref.version): snapshot
            for snapshot in snapshots
        }
        seen: set[tuple[str, int]] = set()
        for entry in artifact.entries:
            key = (entry.record_ref.record_id, entry.record_ref.version)
            if key not in allowed:
                raise self._invalid_error("Index entry references a non-active or out-of-scope Memory.")
            if key in seen:
                raise self._invalid_error("Index staging artifact contains duplicate entries.")
            seen.add(key)
            snapshot = allowed[key]
            if (
                entry.owner_ref != request.principal_ref
                or entry.space_id != request.space_id
                or entry.owner_ref != snapshot.owner_ref
                or entry.space_id != snapshot.space_id
            ):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.owner-space-mismatch",
                        category="unauthorized",
                        message="Index entry owner or space does not match the rebuild boundary.",
                        typed_details={"record_id": entry.record_ref.record_id},
                    )
                )
            if entry.payload_digest != snapshot.payload_digest:
                raise self._invalid_error("Index entry payload digest is stale.")
            if entry.index_revision != request.index_revision:
                raise self._invalid_error("Index entry revision is incorrect.")
        expected_entry_digests = [memory_index_entry_digest(entry) for entry in artifact.entries]
        if artifact.entry_digests and artifact.entry_digests != expected_entry_digests:
            raise self._invalid_error("Index entry digests do not match entry content.")
        artifact.entry_digests = expected_entry_digests
        expected_artifact_digest = memory_index_artifact_digest(artifact)
        if artifact.artifact_digest and artifact.artifact_digest != expected_artifact_digest:
            raise self._invalid_error("Index artifact digest does not match its content.")
        artifact.artifact_digest = expected_artifact_digest

    def _validate_result(
        self,
        result: MemoryIndexRebuildResult,
        request: MemoryIndexRebuildRequest,
        artifact: MemoryIndexBuildArtifact,
    ) -> None:
        if result.index_revision != request.index_revision:
            raise self._invalid_error("Index result revision is incorrect.")
        if result.index_schema_ref != request.index_schema_ref:
            raise self._invalid_error("Index result schema is incorrect.")
        if result.snapshot_digest != artifact.snapshot_digest:
            raise self._invalid_error("Index result snapshot digest is incorrect.")
        if result.result_state == "unavailable":
            if result.entries or result.published:
                raise self._invalid_error("Unavailable Index results cannot publish entries.")
            return
        if result.result_state == "stale":
            if result.entries or result.published:
                raise self._invalid_error("Stale Index results cannot publish entries.")
            return
        if not result.published or result.index_snapshot_ref is None:
            raise self._invalid_error("Complete Index results must publish an index snapshot.")
        if result.entries != artifact.entries:
            raise self._invalid_error("Published Index entries do not match staging.")
        if result.entry_count != len(artifact.entries):
            raise self._invalid_error("Published Index entry count is incorrect.")
        if result.entry_digests != artifact.entry_digests:
            raise self._invalid_error("Published Index entry digests are incorrect.")

    def _discard(
        self, request: MemoryIndexRebuildRequest, artifact: MemoryIndexBuildArtifact
    ) -> None:
        try:
            self.adapter.discard(request, artifact)
        except Exception:
            # A failed discard cannot turn a stale artifact into Canonical state. The next
            # rebuild will use the current snapshot and the adapter remains replaceable.
            return

    def _stale_result(
        self,
        request: MemoryIndexRebuildRequest,
        snapshot_digest: str,
        **details: str,
    ) -> MemoryIndexRebuildResult:
        result = MemoryIndexRebuildResult(
            result_state="stale",
            snapshot_digest=snapshot_digest,
            index_schema_ref=request.index_schema_ref,
            index_revision=request.index_revision,
            failure_detail={"code": "shadow.memory.index-stale", **details},
        )
        return result.model_copy(update={"result_digest": memory_index_result_digest(result)})

    @staticmethod
    def _unavailable_error(message: str) -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(
                code="shadow.memory.index-unavailable",
                category="unavailable",
                message=message,
                retryable=True,
            )
        )

    @staticmethod
    def _invalid_error(message: str) -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(
                code="shadow.memory.index-invalid",
                category="validation",
                message=message,
            )
        )


__all__ = [
    "MemoryIndexAdapter",
    "MemoryIndexBuildArtifact",
    "MemoryIndexEntry",
    "MemoryIndexRebuildRequest",
    "MemoryIndexRebuildResult",
    "MemoryIndexRebuildService",
    "memory_index_artifact_digest",
    "memory_index_entry_digest",
    "memory_index_result_digest",
    "memory_index_snapshot_digest",
]
