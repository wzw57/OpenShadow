from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from pydantic import ValidationError as PydanticValidationError
from shadow_application import (
    IntegrationRegistrationRequest,
    IntegrationRegistrationResult,
    IntegrationService,
)
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import RepositoryUnavailable, ShadowDomainError
from shadow_kernel.models import RecordVersionRef, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_store import SqliteCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "sha256:" + "0" * 64


def _service(tmp_path: Path) -> tuple[SqliteCanonicalRepository, IntegrationService]:
    repository = SqliteCanonicalRepository(tmp_path / "shadow.db")
    registry = ContractRegistry(ROOT)
    authority = CommitAuthority(repository, registry)
    return repository, IntegrationService(repository, authority, registry)


def _request(
    *,
    integration_id: str = "integration-calendar",
    operation: str = "create",
    expected_version: int | None = None,
    key: str = "integration-register-1",
    principal_ref: str = "principal-test",
    space_id: str = "space-test",
    status: str = "enabled",
    lifecycle: str = "active",
) -> IntegrationRegistrationRequest:
    return IntegrationRegistrationRequest(
        principal_ref=principal_ref,
        space_id=space_id,
        integration_id=integration_id,
        provider_kind="shadow.integration.calendar",
        external_ref="provider-account-1",
        config_ref=StableRecordRef(record_id="config-calendar"),
        secret_refs=[StableRecordRef(record_id="secret-calendar")],
        adapter_ref=RecordVersionRef(record_id="adapter-calendar", version=1),
        adapter_descriptor_digest=DIGEST,
        status=status,
        lifecycle=lifecycle,
        health_observation_ref=RecordVersionRef(record_id="health-calendar", version=1),
        operation=operation,
        expected_version=expected_version,
        idempotency_key=key,
    )


def test_integration_fixtures_validate_and_invalid_payload_is_rejected() -> None:
    registry = ContractRegistry(ROOT)
    schema_ref = "https://schemas.openshadow.dev/contracts/integrations/1.0.0#/$defs/IntegrationPayload"
    valid = json.loads(
        (ROOT / "contracts" / "fixtures" / "integrations" / "valid-integration-payload.json").read_text()
    )
    invalid = json.loads(
        (ROOT / "contracts" / "fixtures" / "integrations" / "invalid-integration-payload.json").read_text()
    )
    registry.validate(valid, schema_ref)
    with pytest.raises(ValidationError):
        registry.validate(invalid, schema_ref)


def test_integration_create_persists_refs_without_secret_material(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    result = service.register(_request(),)

    assert isinstance(result, IntegrationRegistrationResult)
    record = repository.get(result.record_ref.record_id)
    assert record is not None
    assert record["record_type"] == "shadow.profile.integration"
    assert record["typed_payload"]["secret_refs"] == [{"record_id": "secret-calendar"}]
    encoded = json.dumps(record)
    assert "do-not-persist" not in encoded
    assert "password" not in encoded.lower()
    assert "token" not in encoded.lower()


def test_integration_replay_is_stable_and_creates_no_version(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    request = _request(key="integration-replay")
    first = service.register(request)
    replay = service.register(request)

    assert replay.result_state == "replayed"
    assert replay.replayed is True
    assert replay.record_ref == first.record_ref
    assert replay.commit_id == first.commit_id
    assert replay.result_digest == first.result_digest
    assert repository.current_version(first.record_ref.record_id) == 1


def test_integration_refresh_preserves_identity_and_status(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = service.register(_request(key="integration-create"))
    second = service.register(
        _request(
            operation="refresh",
            expected_version=1,
            key="integration-refresh",
            status="needs_reauth",
        )
    )

    assert second.record_ref.record_id == first.record_ref.record_id
    assert second.record_ref.version == 2
    assert repository.get(first.record_ref.record_id, 1)["typed_payload"]["status"] == "enabled"
    assert repository.get(first.record_ref.record_id, 2)["typed_payload"]["status"] == "needs_reauth"


def test_integration_refresh_conflict_is_atomic(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    first = service.register(_request(key="integration-create"))
    service.register(
        _request(operation="refresh", expected_version=1, key="integration-refresh-1")
    )
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(
            _request(operation="refresh", expected_version=1, key="integration-refresh-stale")
        )
    assert exc_info.value.error.code == "shadow.integration.version-conflict"
    assert repository.current_version(first.record_ref.record_id) == 2


def test_integration_owner_space_mismatch_is_rejected(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    service.register(_request(key="integration-owner"))
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(
            _request(
                operation="refresh",
                expected_version=1,
                key="integration-owner-mismatch",
                principal_ref="principal-other",
            )
        )
    assert exc_info.value.error.code == "shadow.integration.owner-space-mismatch"


def test_integration_reference_and_secret_material_validation() -> None:
    raw_secret = _request().model_dump(mode="json")
    raw_secret["external_ref"] = "account?token=raw-secret"
    with pytest.raises(PydanticValidationError):
        IntegrationRegistrationRequest.model_validate(raw_secret)
    malformed_digest = _request().model_dump(mode="json")
    malformed_digest["adapter_descriptor_digest"] = "not-a-digest"
    with pytest.raises(PydanticValidationError):
        IntegrationRegistrationRequest.model_validate(malformed_digest)


def test_integration_states_and_health_reference_are_recorded(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    result = service.register(
        _request(key="integration-unavailable", status="unavailable", lifecycle="retired")
    )
    payload = repository.get(result.record_ref.record_id)["typed_payload"]
    assert payload["status"] == "unavailable"
    assert payload["lifecycle"] == "retired"
    assert payload["health_observation_ref"] == {"record_id": "health-calendar", "version": 1}


def test_retired_integration_cannot_be_refreshed(tmp_path: Path) -> None:
    _, service = _service(tmp_path)
    service.register(_request(key="integration-retired", lifecycle="retired"))
    with pytest.raises(ShadowDomainError) as exc_info:
        service.register(
            _request(operation="refresh", expected_version=1, key="integration-retired-refresh")
        )
    assert exc_info.value.error.code == "shadow.integration.not-active"


def test_integration_store_unavailable_and_restart(tmp_path: Path) -> None:
    repository, service = _service(tmp_path)
    repository.set_available(False)
    with pytest.raises(RepositoryUnavailable):
        service.register(_request(key="integration-unavailable-store"))
    repository.set_available(True)
    first = service.register(_request(key="integration-restart"))

    repository2, service2 = _service(tmp_path)
    replay = service2.register(_request(key="integration-restart"))
    assert replay.replayed is True
    assert repository2.current_version(first.record_ref.record_id) == 1
