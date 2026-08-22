from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import Field
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CanonicalEnvelope,
    CommitOperation,
    CommitPlan,
    Provenance,
    RecordVersionRef,
    StableRecordRef,
    StrictModel,
)
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

EXPORT_FORMAT = "shadow.canonical-export"
EXPORT_VERSION = "1.0.0"
IMPORT_RECORD_SCHEMA = "https://schemas.openshadow.dev/contracts/kernel/1.0.0#/$defs/CanonicalEnvelope"


class PortableImportRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    import_id: str = Field(min_length=1, max_length=255)
    identity_mode: Literal["strict", "remap_to_target"] = "strict"
    idempotency_key: str = Field(min_length=1, max_length=255)


class PortableImportRecordResult(StrictModel):
    record_ref: RecordVersionRef
    action: Literal["imported", "skipped_identical"]


class PortableImportResult(StrictModel):
    result_state: Literal["committed", "replayed", "no_change"]
    import_id: str
    source_manifest_digest: str
    imported: list[PortableImportRecordResult] = Field(default_factory=list, max_length=100_000)
    skipped: list[PortableImportRecordResult] = Field(default_factory=list, max_length=100_000)
    commit_id: str | None = None
    replayed: bool = False
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)
    failure_detail: dict[str, Any] | None = None


def portable_import_result_digest(result: PortableImportResult) -> str:
    return sha256_digest(
        {
            "import_id": result.import_id,
            "source_manifest_digest": result.source_manifest_digest,
            "imported": [item.model_dump(mode="json") for item in result.imported],
            "skipped": [item.model_dump(mode="json") for item in result.skipped],
            "commit_id": result.commit_id,
        }
    )


class PortableImportService:
    """Validate and atomically restore one selected portable snapshot."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def restore(
        self, request: PortableImportRequest, bundle: dict[str, Any]
    ) -> PortableImportResult:
        request = PortableImportRequest.model_validate(request)
        if not self.repository.available:
            raise RepositoryUnavailable()
        records, source_manifest_digest = self._read_bundle(bundle)
        records = self._map_identity(records, request)
        request_digest = sha256_digest(
            {
                "request": request.model_dump(mode="json"),
                "source_manifest_digest": source_manifest_digest,
                "records": [self._fingerprint(record) for record in records],
            }
        )
        scope = f"portable-import:{request.principal_ref}:{request.space_id}"
        prior = self.repository.idempotency_result(scope, request.idempotency_key)
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise self._error(
                    "shadow.portable-import.replay-conflict",
                    "Portable import idempotency key was reused with different content.",
                    category="conflict",
                    details={"import_id": request.import_id},
                )
            prior_result = prior["result"]
            if prior_result.outcome in {"committed", "idempotent_replay"}:
                imported_ids = {
                    item.record_id: item.resulting_version
                    for item in prior_result.operation_results
                    if item.resulting_version is not None
                }
                imported = [
                    PortableImportRecordResult(
                        record_ref=RecordVersionRef(
                            record_id=record["record_id"],
                            version=imported_ids[record["record_id"]],
                        ),
                        action="imported",
                    )
                    for record in records
                    if record["record_id"] in imported_ids
                ]
                skipped = [
                    PortableImportRecordResult(
                        record_ref=RecordVersionRef(
                            record_id=record["record_id"], version=record["version"]
                        ),
                        action="skipped_identical",
                    )
                    for record in records
                    if record["record_id"] not in imported_ids
                ]
                result = PortableImportResult(
                    result_state="replayed",
                    import_id=request.import_id,
                    source_manifest_digest=source_manifest_digest,
                    imported=imported,
                    skipped=skipped,
                    commit_id=prior_result.commit_id,
                    replayed=True,
                )
                return result.model_copy(
                    update={"result_digest": portable_import_result_digest(result)}
                )
            if prior_result.outcome == "conflict":
                raise self._error(
                    "shadow.portable-import.version-conflict",
                    "The prior portable import attempt conflicted and was not committed.",
                    category="conflict",
                    details=prior_result.model_dump(mode="json", exclude_none=True),
                )

        operations: list[CommitOperation] = []
        imported: list[PortableImportRecordResult] = []
        skipped: list[PortableImportRecordResult] = []
        for record in records:
            current = self.repository.get(record["record_id"])
            action = self._prepare_record(
                record,
                current=current,
                request=request,
                operations=operations,
            )
            if action is not None:
                skipped.append(action)

        if not operations:
            result = PortableImportResult(
                result_state="no_change",
                import_id=request.import_id,
                source_manifest_digest=source_manifest_digest,
                skipped=skipped,
            )
            return result.model_copy(update={"result_digest": portable_import_result_digest(result)})

        try:
            commit = self.authority.commit(
                CommitPlan(
                    commit_request_id=f"commit-request-{request.import_id}",
                    idempotency_scope=scope,
                    idempotency_key=request.idempotency_key,
                    request_digest=request_digest,
                    actor_ref=request.principal_ref,
                    operations=operations,
                    prepared_at=utc_timestamp(),
                )
            )
        except RepositoryUnavailable:
            raise
        if commit.outcome == "conflict":
            raise self._error(
                "shadow.portable-import.version-conflict",
                "Portable import CAS conflict; no records were imported.",
                category="conflict",
                details=commit.model_dump(mode="json", exclude_none=True),
            )
        if commit.outcome == "failed":
            structured = commit.structured_error or {}
            if structured.get("code") == "shadow.repository.idempotency-mismatch":
                raise self._error(
                    "shadow.portable-import.replay-conflict",
                    "Portable import idempotency key was reused with different content.",
                    category="conflict",
                    details=structured,
                )
            raise self._error(
                "shadow.portable-import.invalid-bundle",
                "Portable import commit was rejected.",
                category="validation",
                details=structured,
            )

        operation_versions = {
            item.record_id: item.resulting_version
            for item in commit.operation_results
            if item.resulting_version is not None
        }
        imported = [
            PortableImportRecordResult(
                record_ref=RecordVersionRef(
                    record_id=record["record_id"], version=operation_versions[record["record_id"]]
                ),
                action="imported",
            )
            for record in records
            if record["record_id"] in operation_versions
        ]
        result = PortableImportResult(
            result_state="committed",
            import_id=request.import_id,
            source_manifest_digest=source_manifest_digest,
            imported=imported,
            skipped=skipped,
            commit_id=commit.commit_id,
            replayed=commit.outcome == "idempotent_replay",
        )
        return result.model_copy(update={"result_digest": portable_import_result_digest(result)})

    def _read_bundle(self, bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        if bundle.get("format") != EXPORT_FORMAT or bundle.get("version") != EXPORT_VERSION:
            raise self._error(
                "shadow.portable-import.invalid-bundle",
                "Portable bundle format or version is not supported.",
            )
        records = bundle.get("records")
        record_digests = bundle.get("record_digests")
        if not isinstance(records, list) or not isinstance(record_digests, dict):
            raise self._error(
                "shadow.portable-import.invalid-bundle",
                "Portable bundle is missing records or record digests.",
            )
        manifest = {
            "format": bundle["format"],
            "version": bundle["version"],
            "records": records,
            "record_digests": record_digests,
        }
        manifest_digest = bundle.get("manifest_digest")
        if manifest_digest != sha256_digest(manifest):
            raise self._error(
                "shadow.portable-import.invalid-bundle",
                "Portable bundle manifest digest does not match its contents.",
            )
        validated: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for raw in records:
            try:
                envelope = CanonicalEnvelope.model_validate(raw).model_dump(
                    mode="json", exclude_none=True
                )
                self.registry.validate_envelope(envelope)
                if envelope["record_state"] == "erased":
                    self.registry.validate(
                        envelope["typed_payload"],
                        "https://schemas.openshadow.dev/contracts/kernel/1.0.0#/$defs/TombstonePayload",
                    )
                else:
                    self.registry.validate(envelope["typed_payload"], envelope["schema_ref"])
            except (ValueError, JsonSchemaValidationError, ShadowDomainError) as exc:
                raise self._error(
                    "shadow.portable-import.invalid-bundle",
                    "Portable bundle contains an invalid Envelope or typed payload.",
                ) from exc
            key = f"{envelope['record_id']}@{envelope['version']}"
            if record_digests.get(key) != sha256_digest(envelope):
                raise self._error(
                    "shadow.portable-import.invalid-bundle",
                    f"Portable bundle record digest mismatch for {key}.",
                )
            if envelope["record_id"] in seen_ids:
                raise self._error(
                    "shadow.portable-import.invalid-bundle",
                    "Portable snapshot contains more than one version for a record.",
                    details={"record_id": envelope["record_id"]},
                )
            seen_ids.add(envelope["record_id"])
            validated.append(envelope)
        validated.sort(key=lambda record: (record["record_id"], record["version"]))
        return validated, manifest_digest

    def _map_identity(
        self, records: list[dict[str, Any]], request: PortableImportRequest
    ) -> list[dict[str, Any]]:
        mapped: list[dict[str, Any]] = []
        for original in records:
            record = deepcopy(original)
            if request.identity_mode == "strict":
                if record["owner_ref"] != request.principal_ref or record["space_id"] != request.space_id:
                    raise self._error(
                        "shadow.portable-import.owner-space-mismatch",
                        "Portable record owner or space does not match the import boundary.",
                        category="unauthorized",
                        details={"record_id": record["record_id"]},
                    )
            else:
                record["owner_ref"] = request.principal_ref
                record["space_id"] = request.space_id
                record["created_by"] = request.principal_ref
            mapped.append(record)
        return mapped

    def _prepare_record(
        self,
        record: dict[str, Any],
        *,
        current: dict[str, Any] | None,
        request: PortableImportRequest,
        operations: list[CommitOperation],
    ) -> PortableImportRecordResult | None:
        if record["record_state"] == "erased" and not record["typed_payload"].get("erased"):
            raise self._error(
                "shadow.portable-import.invalid-bundle",
                "Erased records must contain a Tombstone payload.",
            )
        if current is not None:
            if current["owner_ref"] != request.principal_ref or current["space_id"] != request.space_id:
                raise self._error(
                    "shadow.portable-import.owner-space-mismatch",
                    "Existing record owner or space does not match the import boundary.",
                    category="unauthorized",
                    details={"record_id": record["record_id"]},
                )
            if current["record_state"] == "erased" and record["record_state"] != "erased":
                raise self._error(
                    "shadow.portable-import.version-conflict",
                    "An erased record cannot be resurrected by a portable import.",
                    category="conflict",
                    details={"record_id": record["record_id"]},
                )
            if current["version"] >= record["version"]:
                existing = self.repository.get(record["record_id"], record["version"])
                if existing is not None and self._fingerprint(existing) == self._fingerprint(record):
                    return PortableImportRecordResult(
                        record_ref=RecordVersionRef(
                            record_id=record["record_id"], version=record["version"]
                        ),
                        action="skipped_identical",
                    )
                raise self._error(
                    "shadow.portable-import.version-conflict",
                    "Portable record conflicts with the existing version.",
                    category="conflict",
                    details={"record_id": record["record_id"], "current_version": current["version"]},
                )
            if record["version"] != current["version"] + 1:
                raise self._error(
                    "shadow.portable-import.version-conflict",
                    "Portable record has a version gap.",
                    category="conflict",
                    details={"record_id": record["record_id"], "current_version": current["version"]},
                )
            expected_version = current["version"]
            operation = "update"
        else:
            if record["version"] != 1:
                raise self._error(
                    "shadow.portable-import.version-conflict",
                    "A new portable record must start at version 1.",
                    category="conflict",
                    details={"record_id": record["record_id"], "version": record["version"]},
                )
            expected_version = None
            operation = "create"

        operations.append(
            CommitOperation(
                operation_id=f"operation-import-{record['record_id']}-{record['version']}",
                operation=operation,
                record_id=record["record_id"],
                record_type=record["record_type"],
                target_schema_ref=(
                    "https://schemas.openshadow.dev/contracts/kernel/1.0.0#/$defs/TombstonePayload"
                    if record["record_state"] == "erased"
                    else record["schema_ref"]
                ),
                owner_ref=request.principal_ref,
                space_id=request.space_id,
                created_by=record["created_by"],
                data_classification=record["data_classification"],
                provenance=Provenance(
                    origin_type="shadow.origin.portable-import",
                    origin_ref=request.import_id,
                ),
                retention_policy_ref=StableRecordRef(record_id="retention-default"),
                record_state=record["record_state"],
                typed_payload=record["typed_payload"],
                expected_version=expected_version,
            )
        )
        return None

    @staticmethod
    def _fingerprint(record: dict[str, Any]) -> str:
        value = deepcopy(record)
        value.pop("created_at", None)
        value.pop("committed_at", None)
        value.pop("created_by", None)
        value.pop("provenance", None)
        return sha256_digest(value)

    @staticmethod
    def _error(
        code: str,
        message: str,
        *,
        category: Literal["validation", "conflict", "unauthorized"] = "validation",
        details: Any | None = None,
    ) -> ShadowDomainError:
        return ShadowDomainError(
            ShadowError(code=code, category=category, message=message, typed_details=details)
        )


__all__ = [
    "PortableImportRecordResult",
    "PortableImportRequest",
    "PortableImportResult",
    "PortableImportService",
    "portable_import_result_digest",
]
