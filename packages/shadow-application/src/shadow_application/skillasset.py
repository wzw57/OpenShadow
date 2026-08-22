from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import Field, model_validator
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError, ShadowError
from shadow_kernel.ids import canonical_json, sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    Provenance,
    RecordVersionRef,
    StrictModel,
)
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

SKILL_SCHEMA = "https://schemas.openshadow.dev/contracts/skills/1.0.0"
SKILL_PAYLOAD_SCHEMA = f"{SKILL_SCHEMA}#/$defs/SkillAssetPayload"
SKILL_MANIFEST_SCHEMA = f"{SKILL_SCHEMA}#/$defs/SkillBundleManifest"
SKILL_RECORD_TYPE = "shadow.profile.skill-asset"
RETENTION_REF = RecordVersionRef(record_id="retention-default", version=1)


class SkillBundleFile(StrictModel):
    relative_path: str = Field(min_length=1, max_length=1000)
    byte_length: int = Field(ge=0)
    sha256: str = Field(min_length=1, max_length=71)


class SkillBundleManifest(StrictModel):
    digest_format: Literal["shadow.skill-bundle-digest.v1"]
    files: list[SkillBundleFile] = Field(min_length=1, max_length=100_000)


class SkillAssetRegistrationRequest(StrictModel):
    principal_ref: str = Field(min_length=1, max_length=255)
    space_id: str = Field(min_length=1, max_length=255)
    skill_id: str = Field(min_length=1, max_length=80)
    source_ref: str = Field(min_length=1, max_length=1000)
    pinned_revision: str | None = Field(default=None, min_length=1, max_length=500)
    snapshot_artifact_ref: RecordVersionRef | None = None
    bundle_digest: str = Field(min_length=1, max_length=71)
    trust: Literal["untrusted", "reviewed", "trusted"] = "untrusted"
    permission_policy_ref: RecordVersionRef
    data_classification: Literal["public", "personal", "sensitive", "restricted"] = "personal"
    install_state: Literal["discovered", "installed", "disabled", "invalid"] = "discovered"
    runtime_projection_refs: list[str] = Field(default_factory=list, max_length=100)
    provider_external_refs: list[str] = Field(default_factory=list, max_length=100)
    operation: Literal["create", "refresh"] = "create"
    expected_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_operation(self) -> SkillAssetRegistrationRequest:
        if self.pinned_revision is None and self.snapshot_artifact_ref is None:
            raise ValueError("pinned_revision or snapshot_artifact_ref is required")
        if self.operation == "create" and self.expected_version is not None:
            raise ValueError("create cannot include expected_version")
        if self.operation == "refresh" and self.expected_version is None:
            raise ValueError("refresh requires expected_version")
        if len(set(self.runtime_projection_refs)) != len(self.runtime_projection_refs):
            raise ValueError("runtime_projection_refs must be unique")
        if len(set(self.provider_external_refs)) != len(self.provider_external_refs):
            raise ValueError("provider_external_refs must be unique")
        return self


class SkillAssetRegistrationResult(StrictModel):
    result_state: Literal["committed", "replayed"]
    skill_id: str
    record_ref: RecordVersionRef
    bundle_digest: str
    commit_id: str | None = None
    replayed: bool = False
    result_digest: str = ""
    generated_at: str = Field(default_factory=utc_timestamp)


def skill_bundle_manifest(root: str | Path) -> SkillBundleManifest:
    """Build the canonical, byte-based manifest for a standard Agent Skills directory."""

    bundle_root = Path(root)
    if bundle_root.is_symlink():
        raise _invalid("Skill bundle root cannot be a symbolic link.", {"root": str(root)})
    try:
        bundle_root = bundle_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _invalid("Skill bundle root is not readable.", {"root": str(root)}) from exc
    if not bundle_root.is_dir():
        raise _invalid("Skill bundle root must be a directory.", {"root": str(root)})

    files: list[SkillBundleFile] = []
    seen: set[str] = set()
    try:
        entries = sorted(bundle_root.rglob("*"), key=lambda path: path.as_posix())
        for path in entries:
            if path.is_symlink():
                raise _invalid("Skill bundles cannot contain symbolic links.", {"path": str(path)})
            if not path.is_file():
                continue
            relative = path.relative_to(bundle_root).as_posix()
            if (
                not relative
                or relative.startswith("/")
                or "\\" in relative
                or any(part in {"", ".", ".."} for part in relative.split("/"))
            ):
                raise _invalid("Skill bundle path is not a safe POSIX relative path.", {"path": relative})
            if relative in seen:
                raise _invalid("Skill bundle contains duplicate normalized paths.", {"path": relative})
            seen.add(relative)
            data = path.read_bytes()
            files.append(
                SkillBundleFile(
                    relative_path=relative,
                    byte_length=len(data),
                    sha256=f"sha256:{hashlib.sha256(data).hexdigest()}",
                )
            )
    except (OSError, ValueError) as exc:
        if isinstance(exc, ShadowDomainError):
            raise
        raise _invalid("Skill bundle could not be enumerated.", {"root": str(root)}) from exc
    if not files:
        raise _invalid("Skill bundle must contain at least one regular file.", {"root": str(root)})
    files.sort(key=lambda item: item.relative_path)
    return SkillBundleManifest(digest_format="shadow.skill-bundle-digest.v1", files=files)


def skill_bundle_digest(manifest: SkillBundleManifest | dict[str, Any]) -> str:
    value = SkillBundleManifest.model_validate(manifest).model_dump(mode="json")
    return f"sha256:{hashlib.sha256(canonical_json(value)).hexdigest()}"


def skill_asset_result_digest(result: SkillAssetRegistrationResult) -> str:
    return sha256_digest(
        {
            "skill_id": result.skill_id,
            "record_ref": result.record_ref.model_dump(mode="json"),
            "bundle_digest": result.bundle_digest,
            "commit_id": result.commit_id,
        }
    )


class SkillAssetService:
    """Register and refresh SkillAsset governance sidecars through CommitAuthority."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def register(
        self, request: SkillAssetRegistrationRequest, *, bundle_root: str | Path
    ) -> SkillAssetRegistrationResult:
        request = SkillAssetRegistrationRequest.model_validate(request)
        if not self.repository.available:
            raise RepositoryUnavailable()
        manifest = skill_bundle_manifest(bundle_root)
        try:
            self.registry.validate(manifest.model_dump(mode="json"), SKILL_MANIFEST_SCHEMA)
        except JsonSchemaValidationError as exc:
            raise _invalid(
                "Skill bundle manifest does not satisfy the contract.",
                {"path": list(exc.absolute_path), "detail": exc.message},
            ) from exc
        actual_digest = skill_bundle_digest(manifest)
        if actual_digest != request.bundle_digest:
            raise _invalid(
                "Declared Skill bundle digest does not match the bundle bytes.",
                {"declared": request.bundle_digest, "actual": actual_digest},
            )

        payload: dict[str, Any] = {
            "skill_id": request.skill_id,
            "format": "agent-skills",
            "source_ref": request.source_ref,
            "bundle_digest": actual_digest,
            "trust": request.trust,
            "permission_policy_ref": request.permission_policy_ref.model_dump(mode="json"),
            "data_classification": request.data_classification,
            "install_state": request.install_state,
            "runtime_projection_refs": list(request.runtime_projection_refs),
            "provider_external_refs": list(request.provider_external_refs),
        }
        if request.pinned_revision is not None:
            payload["pinned_revision"] = request.pinned_revision
        if request.snapshot_artifact_ref is not None:
            payload["snapshot_artifact_ref"] = request.snapshot_artifact_ref.model_dump(mode="json")
        try:
            self.registry.validate(payload, SKILL_PAYLOAD_SCHEMA)
        except JsonSchemaValidationError as exc:
            raise _invalid(
                "SkillAsset sidecar does not satisfy its contract.",
                {"path": list(exc.absolute_path), "detail": exc.message},
            ) from exc

        record_id = _skill_record_id(request.skill_id)
        current = self.repository.get(record_id)
        if current is not None and (
            current["owner_ref"] != request.principal_ref or current["space_id"] != request.space_id
        ):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.skill-asset.owner-space-mismatch",
                    category="unauthorized",
                    message="SkillAsset owner or space does not match the registration principal.",
                    typed_details={"record_id": record_id},
                )
            )
        if request.operation == "refresh":
            if current is None:
                raise _invalid("SkillAsset refresh target was not found.", {"record_id": record_id})
            if current["record_type"] != SKILL_RECORD_TYPE:
                raise _invalid("SkillAsset identity is occupied by another record type.", {"record_id": record_id})
            if current["record_state"] != "active":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.skill-asset.not-active",
                        category="conflict",
                        message="A non-active SkillAsset cannot be refreshed.",
                        typed_details={"record_id": record_id, "current_version": current["version"]},
                    )
                )

        operation = CommitOperation(
            operation_id=f"operation-{record_id}-{request.operation}-{request.idempotency_key}",
            operation="create" if request.operation == "create" else "update",
            record_id=record_id,
            record_type=SKILL_RECORD_TYPE,
            target_schema_ref=SKILL_PAYLOAD_SCHEMA,
            owner_ref=request.principal_ref,
            space_id=request.space_id,
            created_by=request.principal_ref,
            data_classification=request.data_classification,
            provenance=Provenance(
                origin_type="shadow.origin.user-command",
                origin_ref=f"skill-asset-registration-{request.skill_id}",
            ),
            retention_policy_ref=RecordVersionRef(record_id="retention-default", version=1),
            typed_payload=payload,
            expected_version=request.expected_version,
        )
        request_digest = sha256_digest(
            {
                "request": request.model_dump(mode="json", exclude_none=True),
                "manifest": manifest.model_dump(mode="json"),
            }
        )
        try:
            commit = self.authority.commit(
                CommitPlan(
                    commit_request_id=f"commit-request-{record_id}-{request.idempotency_key}",
                    idempotency_scope=f"skill-asset:{request.principal_ref}:{request.space_id}",
                    idempotency_key=request.idempotency_key,
                    request_digest=request_digest,
                    actor_ref=request.principal_ref,
                    operations=[operation],
                    prepared_at=utc_timestamp(),
                )
            )
        except RepositoryUnavailable:
            raise
        except ShadowDomainError:
            raise

        if commit.outcome == "conflict":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.skill-asset.version-conflict",
                    category="conflict",
                    message="SkillAsset expected version does not match the current head.",
                    typed_details=commit.model_dump(mode="json", exclude_none=True),
                )
            )
        if commit.outcome == "failed":
            structured = commit.structured_error or {}
            if structured.get("code") == "shadow.repository.idempotency-mismatch":
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.skill-asset.replay-conflict",
                        category="conflict",
                        message="SkillAsset idempotency key was reused with different content.",
                        typed_details=structured,
                    )
                )
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.skill-asset.commit-failed",
                    category="validation",
                    message="SkillAsset sidecar could not be committed.",
                    typed_details=structured,
                )
            )

        operation_result = commit.operation_results[0]
        resulting_version = operation_result.resulting_version
        if resulting_version is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.skill-asset.commit-missing-result",
                    category="internal",
                    message="SkillAsset commit did not return a resulting version.",
                )
            )
        result = SkillAssetRegistrationResult(
            result_state="replayed" if commit.outcome == "idempotent_replay" else "committed",
            skill_id=request.skill_id,
            record_ref=RecordVersionRef(record_id=record_id, version=resulting_version),
            bundle_digest=actual_digest,
            commit_id=commit.commit_id,
            replayed=commit.outcome == "idempotent_replay",
        )
        return result.model_copy(update={"result_digest": skill_asset_result_digest(result)})


def _skill_record_id(skill_id: str) -> str:
    return f"skill-asset-{sha256_digest({'skill_id': skill_id})[7:39]}"


def _invalid(message: str, details: dict[str, Any] | None = None) -> ShadowDomainError:
    return ShadowDomainError(
        ShadowError(
            code="shadow.skill-asset.invalid",
            category="validation",
            message=message,
            typed_details=details,
        )
    )


__all__ = [
    "SkillAssetRegistrationRequest",
    "SkillAssetRegistrationResult",
    "SkillAssetService",
    "SkillBundleFile",
    "SkillBundleManifest",
    "skill_asset_result_digest",
    "skill_bundle_digest",
    "skill_bundle_manifest",
]
