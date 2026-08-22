from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from shadow_application import (
    SkillAssetRegistrationRequest,
    SkillAssetService,
    skill_bundle_digest,
    skill_bundle_manifest,
)
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError
from shadow_kernel.models import RecordVersionRef
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "contracts" / "fixtures" / "agent-skills" / "minimal-valid" / "minimal-valid"
COMPLETE = ROOT / "contracts" / "fixtures" / "agent-skills" / "complete-valid" / "complete-valid"
CHANGED_BEFORE = ROOT / "contracts" / "fixtures" / "agent-skills" / "digest-changed" / "before" / "digest-changed"
CHANGED_AFTER = ROOT / "contracts" / "fixtures" / "agent-skills" / "digest-changed" / "after" / "digest-changed"


def _service(tmp_path: Path) -> tuple[SqliteCanonicalRepository, SkillAssetService]:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, SkillAssetService(repository, authority, registry)


def _request(
    *,
    digest: str,
    skill_id: str = "skill-minimal",
    operation: str = "create",
    expected_version: int | None = None,
    key: str = "skill-register-1",
    principal_ref: str = "principal-test",
    space_id: str = "space-test",
) -> SkillAssetRegistrationRequest:
    return SkillAssetRegistrationRequest(
        principal_ref=principal_ref,
        space_id=space_id,
        skill_id=skill_id,
        source_ref="file:///skills/minimal",
        pinned_revision="rev-1",
        bundle_digest=digest,
        trust="untrusted",
        permission_policy_ref=RecordVersionRef(record_id="policy-default", version=1),
        data_classification="personal",
        install_state="discovered",
        operation=operation,
        expected_version=expected_version,
        idempotency_key=key,
    )


def _minimal_digest() -> str:
    return skill_bundle_digest(skill_bundle_manifest(MINIMAL))


def test_bundle_digest_matches_pinned_fixture_and_changes_with_bytes() -> None:
    assert _minimal_digest() == "sha256:430812684d7eb33aece994b0e15f407f28b16366a428b9d92c0467c7d1b7329d"
    before = skill_bundle_digest(skill_bundle_manifest(CHANGED_BEFORE))
    after = skill_bundle_digest(skill_bundle_manifest(CHANGED_AFTER))
    assert before == "sha256:630d15242089982bbb87f39e08cca6aa9cb686965700201456a1ebccbce01a12"
    assert after == "sha256:027aaa8a4b2496319d277952c8f19e14e892abdfc4608e83d2ca5a617831756c"
    assert before != after


def test_complete_bundle_manifest_is_sorted_and_schema_valid() -> None:
    manifest = skill_bundle_manifest(COMPLETE)
    assert [item.relative_path for item in manifest.files] == sorted(
        item.relative_path for item in manifest.files
    )
    ContractRegistry(ROOT).validate(
        manifest.model_dump(mode="json"),
        "https://schemas.openshadow.dev/contracts/skills/1.0.0#/$defs/SkillBundleManifest",
    )


def test_skillasset_sidecar_fixtures_validate_and_reject_capability_grant() -> None:
    registry = ContractRegistry(ROOT)
    schema_ref = "https://schemas.openshadow.dev/contracts/skills/1.0.0#/$defs/SkillAssetPayload"
    valid = json.loads(
        (ROOT / "contracts" / "fixtures" / "agent-skills" / "valid-registration-result.json").read_text()
    )
    invalid = json.loads(
        (ROOT / "contracts" / "fixtures" / "agent-skills" / "invalid-registration-result.json").read_text()
    )
    registry.validate(valid, schema_ref)
    with pytest.raises(ValidationError):
        registry.validate(invalid, schema_ref)


def test_invalid_path_manifest_fixture_is_rejected() -> None:
    registry = ContractRegistry(ROOT)
    invalid = json.loads(
        (ROOT / "contracts" / "fixtures" / "agent-skills" / "invalid-path-traversal" / "manifest.json").read_text()
    )
    with pytest.raises(ValidationError):
        registry.validate(
            invalid,
            "https://schemas.openshadow.dev/contracts/skills/1.0.0#/$defs/SkillBundleManifest",
        )


def test_skillasset_create_commits_governance_sidecar_only(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    result = service.register(_request(digest=_minimal_digest()), bundle_root=MINIMAL)

    assert result.result_state == "committed"
    assert result.replayed is False
    assert result.record_ref.version == 1
    record = repository.get(result.record_ref.record_id)
    assert record is not None
    assert record["record_type"] == "shadow.profile.skill-asset"
    assert record["typed_payload"]["bundle_digest"] == _minimal_digest()
    assert "SKILL.md" not in json.dumps(record["typed_payload"])
    assert "allowed_tools" not in record["typed_payload"]


def test_skillasset_replay_is_stable_and_does_not_create_a_version(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    request = _request(digest=_minimal_digest(), key="skill-replay")
    first = service.register(request, bundle_root=MINIMAL)
    replay = service.register(request, bundle_root=MINIMAL)

    assert replay.result_state == "replayed"
    assert replay.replayed is True
    assert replay.record_ref == first.record_ref
    assert replay.commit_id == first.commit_id
    assert replay.result_digest == first.result_digest
    assert repository.current_version(first.record_ref.record_id) == 1


def test_skillasset_refresh_preserves_identity_and_old_version(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = service.register(_request(digest=_minimal_digest(), key="skill-create"), bundle_root=MINIMAL)
    refresh = _request(
        digest=skill_bundle_digest(skill_bundle_manifest(COMPLETE)),
        operation="refresh",
        expected_version=1,
        key="skill-refresh",
    ).model_copy(update={"skill_id": "skill-minimal"})
    second = service.register(refresh, bundle_root=COMPLETE)

    assert second.record_ref.record_id == first.record_ref.record_id
    assert second.record_ref.version == 2
    assert repository.get(first.record_ref.record_id, 1)["typed_payload"]["bundle_digest"] == _minimal_digest()
    assert repository.get(first.record_ref.record_id, 2)["typed_payload"]["bundle_digest"] != _minimal_digest()


def test_skillasset_refresh_expected_version_conflict_is_atomic(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = service.register(_request(digest=_minimal_digest(), key="skill-create"), bundle_root=MINIMAL)
    service.register(
        _request(
            digest=skill_bundle_digest(skill_bundle_manifest(COMPLETE)),
            operation="refresh",
            expected_version=1,
            key="skill-refresh-1",
        ),
        bundle_root=COMPLETE,
    )
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(
            _request(
                digest=_minimal_digest(),
                operation="refresh",
                expected_version=1,
                key="skill-refresh-stale",
            ),
            bundle_root=MINIMAL,
        )
    assert exc_info.value.error.code == "shadow.skill-asset.version-conflict"
    assert repository.current_version(first.record_ref.record_id) == 2


def test_skillasset_owner_space_mismatch_is_rejected(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    service.register(_request(digest=_minimal_digest(), key="skill-owner"), bundle_root=MINIMAL)
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(
            _request(
                digest=_minimal_digest(),
                operation="refresh",
                expected_version=1,
                key="skill-owner-mismatch",
                principal_ref="principal-other",
            ),
            bundle_root=MINIMAL,
        )
    assert exc_info.value.error.code == "shadow.skill-asset.owner-space-mismatch"


def test_skillasset_digest_tamper_and_store_unavailable_do_not_commit(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(_request(digest="sha256:" + "0" * 64), bundle_root=MINIMAL)
    assert exc_info.value.error.code == "shadow.skill-asset.invalid"

    repository.set_available(False)
    with pytest.raises(RepositoryUnavailable):
        service.register(_request(digest=_minimal_digest(), key="skill-unavailable"), bundle_root=MINIMAL)


def test_allowed_tools_fixture_does_not_grant_capability(tmp_path: Path) -> None:
    allowed = ROOT / "contracts" / "fixtures" / "agent-skills" / "allowed-tools-untrusted" / "allowed-tools-untrusted"
    digest = skill_bundle_digest(skill_bundle_manifest(allowed))
    _, service = _service(tmp_path)
    result = service.register(
        _request(digest=digest, skill_id="skill-allowed", key="skill-allowed"), bundle_root=allowed
    )
    assert result.result_state == "committed"
    assert "capability" not in result.model_dump(mode="json")


def test_skillasset_restart_recovers_version_and_digest(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = service.register(_request(digest=_minimal_digest(), key="skill-restart"), bundle_root=MINIMAL)
    del repository, service
    repository2, service2 = _service(tmp_path)
    # The fresh service points at the same SQLite file and can replay the durable registration.
    replay = service2.register(_request(digest=_minimal_digest(), key="skill-restart"), bundle_root=MINIMAL)
    assert replay.replayed is True
    assert repository2.current_version(first.record_ref.record_id) == 1
    assert repository2.get(first.record_ref.record_id)["typed_payload"]["bundle_digest"] == _minimal_digest()
