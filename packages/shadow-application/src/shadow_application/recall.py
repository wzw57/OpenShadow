from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import Field, model_validator
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import RecordVersionRef, StableRecordRef, StrictModel
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

PROFILE_SCHEMA = "https://schemas.openshadow.dev/contracts/profiles/1.0.0"


class MemoryRecallQuery(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    query_ref: str | None = Field(default=None, min_length=1, max_length=1000)
    query_text: str | None = Field(default=None, min_length=1, max_length=4000)
    memory_kinds: list[str] = Field(default_factory=list, max_length=32)
    applicability_scope: dict[str, Any] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=2000)
    consistency: Literal["canonical", "bounded_stale"] = "canonical"
    request_id: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_query_reference(self) -> MemoryRecallQuery:
        if self.query_ref is None and self.query_text is None:
            raise ValueError("query_ref or query_text is required")
        return self


class MemorySnapshot(StrictModel):
    record_ref: RecordVersionRef
    owner_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    payload_digest: str = Field(min_length=1, max_length=255)
    record: dict[str, Any]
    is_current_head: bool = True


class MemoryRecallItem(StrictModel):
    record_ref: RecordVersionRef
    match_kind: str = Field(min_length=1, max_length=100)
    score: float | None = Field(default=None, ge=0, le=1)
    index_snapshot_ref: StableRecordRef | None = None


class MemoryRecallResult(StrictModel):
    result_state: Literal["complete", "stale", "unavailable"]
    items: list[MemoryRecallItem] = Field(default_factory=list, max_length=100)
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)
    next_cursor: str | None = None
    index_snapshot_ref: StableRecordRef | None = None
    failure_detail: dict[str, Any] | None = None


class MemoryMaintenanceRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    request_id: str = Field(min_length=1, max_length=255)
    targets: list[RecordVersionRef] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=4000)
    source_refs: list[str] = Field(default_factory=list, max_length=100)
    budget_limit: int = Field(default=100, ge=1, le=10_000)

    @model_validator(mode="after")
    def require_unique_targets(self) -> MemoryMaintenanceRequest:
        refs = [(target.record_id, target.version) for target in self.targets]
        if len(refs) != len(set(refs)):
            raise ValueError("targets must be unique")
        return self


class MemoryMaintenanceResult(StrictModel):
    result_state: Literal["complete", "partial", "unavailable"]
    proposals: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    proposal_digests: list[str] = Field(default_factory=list, max_length=100)
    result_digest: str = ""
    adapter_version: str = Field(min_length=1, max_length=100)
    generated_at: str = Field(default_factory=utc_timestamp)
    failure_detail: dict[str, Any] | None = None


class MemoryRecallAdapter(Protocol):
    adapter_version: str

    def recall(
        self, query: MemoryRecallQuery, snapshots: list[MemorySnapshot]
    ) -> MemoryRecallResult: ...


class MemoryMaintenanceAdapter(Protocol):
    adapter_version: str

    def maintain(
        self, request: MemoryMaintenanceRequest, snapshots: list[MemorySnapshot]
    ) -> MemoryMaintenanceResult: ...


class MemoryRecallService:
    """Read-only Recall boundary over Canonical active Memory heads."""

    def __init__(self, repository: CanonicalRepository, adapter: MemoryRecallAdapter) -> None:
        self.repository = repository
        self.adapter = adapter

    def recall(self, query: MemoryRecallQuery) -> MemoryRecallResult:
        query = MemoryRecallQuery.model_validate(query)
        snapshots = self._active_snapshots(
            query.principal_ref,
            query.space_id,
            include_history=query.consistency == "bounded_stale",
        )
        snapshots = [snapshot for snapshot in snapshots if self._matches_query(snapshot, query)]
        try:
            result = MemoryRecallResult.model_validate(self.adapter.recall(query, snapshots))
        except ShadowDomainError:
            raise
        except Exception as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.recall-unavailable",
                    category="unavailable",
                    message="Recall Adapter failed to return a result.",
                    retryable=True,
                    typed_details={"adapter_version": self._adapter_version()},
                )
            ) from exc
        self._validate_recall_result(result, snapshots, query)
        digest = self._recall_digest(result)
        if result.result_digest and result.result_digest != digest:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.recall-invalid",
                    category="validation",
                    message="Recall result digest does not match its result content.",
                )
            )
        return result.model_copy(update={"result_digest": digest})

    def _active_snapshots(
        self, owner_ref: str, space_id: str, *, include_history: bool = False
    ) -> list[MemorySnapshot]:
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.recall-unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable for Recall.",
                    retryable=True,
                )
            )
        records = self.repository.query(
            owner_refs={owner_ref},
            space_ids={space_id},
            record_types={"shadow.profile.memory"},
            record_states={"active", "logically_deleted", "erased"},
        )
        heads: dict[str, dict[str, Any]] = {}
        for record in records:
            prior = heads.get(record["record_id"])
            if prior is None or record["version"] > prior["version"]:
                heads[record["record_id"]] = record
        snapshots: list[MemorySnapshot] = []
        active_records = records if include_history else list(heads.values())
        for record in sorted(active_records, key=lambda item: (item["record_id"], item["version"])):
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
                    is_current_head=record["version"] == heads[record["record_id"]]["version"],
                )
            )
        return snapshots

    @staticmethod
    def _matches_query(snapshot: MemorySnapshot, query: MemoryRecallQuery) -> bool:
        payload = snapshot.record["typed_payload"]
        if query.memory_kinds and payload.get("memory_kind") not in query.memory_kinds:
            return False
        if query.applicability_scope is None:
            return True
        actual = payload.get("applicability_scope", {})
        requested = query.applicability_scope
        if actual.get("scope_kind") != requested.get("scope_kind"):
            return False
        actual_refs = {ref.get("record_id") for ref in actual.get("scope_refs", [])}
        requested_refs = {ref.get("record_id") for ref in requested.get("scope_refs", [])}
        return requested_refs <= actual_refs

    def _validate_recall_result(
        self,
        result: MemoryRecallResult,
        snapshots: list[MemorySnapshot],
        query: MemoryRecallQuery,
    ) -> None:
        if result.result_state == "unavailable" and result.items:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.recall-invalid",
                    category="validation",
                    message="Unavailable Recall results cannot contain items.",
                )
            )
        allowed = {
            (snapshot.record_ref.record_id, snapshot.record_ref.version) for snapshot in snapshots
        }
        current_heads = {
            (snapshot.record_ref.record_id, snapshot.record_ref.version)
            for snapshot in snapshots
            if snapshot.is_current_head
        }
        if len(result.items) > query.limit:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.recall-invalid",
                    category="validation",
                    message="Recall Adapter returned more items than requested.",
                    typed_details={"limit": query.limit, "actual": len(result.items)},
                )
            )
        for item in result.items:
            key = (item.record_ref.record_id, item.record_ref.version)
            if key not in allowed:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.recall-invalid",
                        category="validation",
                        message="Recall result references a non-active or out-of-scope Memory.",
                        typed_details={
                            "record_id": item.record_ref.record_id,
                            "version": item.record_ref.version,
                        },
                    )
                )
            if key not in current_heads and result.result_state != "stale":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.recall-stale",
                        category="conflict",
                        message="Recall returned a historical version without stale state.",
                        typed_details={
                            "record_id": item.record_ref.record_id,
                            "version": item.record_ref.version,
                        },
                    )
                )

    @staticmethod
    def _recall_digest(result: MemoryRecallResult) -> str:
        return sha256_digest(
            {
                "result_state": result.result_state,
                "items": [item.model_dump(mode="json", exclude_none=True) for item in result.items],
                "next_cursor": result.next_cursor,
                "index_snapshot_ref": result.index_snapshot_ref.model_dump(mode="json")
                if result.index_snapshot_ref
                else None,
            }
        )

    def _adapter_version(self) -> str:
        return str(getattr(self.adapter, "adapter_version", "unknown"))


class MemoryMaintenanceService:
    """Maintenance Adapter boundary; this service never commits proposals."""

    def __init__(
        self,
        repository: CanonicalRepository,
        registry: ContractRegistry,
        adapter: MemoryMaintenanceAdapter,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.adapter = adapter

    def maintain(self, request: MemoryMaintenanceRequest) -> MemoryMaintenanceResult:
        request = MemoryMaintenanceRequest.model_validate(request)
        snapshots = self._target_snapshots(request)
        try:
            result = MemoryMaintenanceResult.model_validate(
                self.adapter.maintain(request, snapshots)
            )
        except ShadowDomainError:
            raise
        except Exception as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-unavailable",
                    category="unavailable",
                    message="Maintenance Adapter failed to return a result.",
                    retryable=True,
                    typed_details={"adapter_version": self._adapter_version()},
                )
            ) from exc
        self._validate_result(result, request, snapshots)
        result_digest = sha256_digest(
            {
                "result_state": result.result_state,
                "proposal_digests": result.proposal_digests,
                "adapter_version": result.adapter_version,
            }
        )
        if result.result_digest and result.result_digest != result_digest:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-invalid",
                    category="validation",
                    message="Maintenance result digest does not match its result content.",
                )
            )
        return result.model_copy(update={"result_digest": result_digest})

    def _target_snapshots(self, request: MemoryMaintenanceRequest) -> list[MemorySnapshot]:
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable for Maintenance.",
                    retryable=True,
                )
            )
        snapshots: list[MemorySnapshot] = []
        for target in request.targets:
            head = self.repository.get(target.record_id)
            record = self.repository.get(target.record_id, target.version)
            if head is None or record is None:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.not-found",
                        category="validation",
                        message=f"Memory {target.record_id} was not found.",
                        typed_details={"record_id": target.record_id, "version": target.version},
                    )
                )
            if (
                head["owner_ref"] != request.principal_ref
                or head["space_id"] != request.space_id
                or record["owner_ref"] != request.principal_ref
                or record["space_id"] != request.space_id
            ):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.owner-space-mismatch",
                        category="unauthorized",
                        message="Maintenance target owner or space does not match the request.",
                        typed_details={"record_id": target.record_id},
                    )
                )
            if (
                head["version"] != target.version
                or record["record_state"] != "active"
                or record["typed_payload"].get("memory_state") != "active"
            ):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.head-not-active",
                        category="conflict",
                        message=f"Memory {target.record_id} is not an active Memory head.",
                        typed_details={
                            "record_id": target.record_id,
                            "current_version": head["version"],
                        },
                    )
                )
            snapshots.append(self._snapshot(record))
        return snapshots

    def _validate_result(
        self,
        result: MemoryMaintenanceResult,
        request: MemoryMaintenanceRequest,
        snapshots: list[MemorySnapshot],
    ) -> None:
        if result.result_state == "unavailable" and result.proposals:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-invalid",
                    category="validation",
                    message="Unavailable Maintenance results cannot contain proposals.",
                )
            )
        allowed = {
            (snapshot.record_ref.record_id, snapshot.record_ref.version) for snapshot in snapshots
        }
        proposal_digests: list[str] = []
        for proposal in result.proposals:
            try:
                self.registry.validate(proposal, f"{PROFILE_SCHEMA}#/$defs/MemoryProposalPayload")
            except Exception as exc:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.maintenance-invalid",
                        category="validation",
                        message="Maintenance proposal does not satisfy the Memory Profile contract.",
                    )
                ) from exc
            if proposal["proposed_operation"] == "create":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.memory.maintenance-invalid",
                        category="validation",
                        message="Maintenance cannot emit a create proposal.",
                    )
                )
            for target in proposal["targets"]:
                key = (target["memory_ref"]["record_id"], target["expected_version"])
                if key not in allowed:
                    raise ShadowDomainError(
                        ShadowError(
                            code="shadow.memory.maintenance-invalid",
                            category="validation",
                            message="Maintenance proposal references a target outside its snapshot.",
                            typed_details={"record_id": key[0], "version": key[1]},
                        )
                    )
            proposal_digests.append(sha256_digest(proposal))
        if result.proposal_digests and result.proposal_digests != proposal_digests:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-invalid",
                    category="validation",
                    message="Maintenance proposal digests do not match proposal content.",
                )
            )
        if not result.proposal_digests:
            result.proposal_digests.extend(proposal_digests)
        if request.budget_limit < len(result.proposals):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.memory.maintenance-invalid",
                    category="validation",
                    message="Maintenance Adapter exceeded the request budget.",
                )
            )

    @staticmethod
    def _snapshot(record: dict[str, Any]) -> MemorySnapshot:
        ref = RecordVersionRef(record_id=record["record_id"], version=record["version"])
        return MemorySnapshot(
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

    def _adapter_version(self) -> str:
        return str(getattr(self.adapter, "adapter_version", "unknown"))


__all__ = [
    "MemoryMaintenanceAdapter",
    "MemoryMaintenanceRequest",
    "MemoryMaintenanceResult",
    "MemoryMaintenanceService",
    "MemoryRecallAdapter",
    "MemoryRecallItem",
    "MemoryRecallQuery",
    "MemoryRecallResult",
    "MemoryRecallService",
    "MemorySnapshot",
]
