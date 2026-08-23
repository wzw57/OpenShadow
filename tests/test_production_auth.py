from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from shadow_application import DeterministicAuthVerifier, SessionService, StaticSecretResolver
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.registry import ContractRegistry
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_session_create_verify_revoke_and_replay() -> None:
    repository = SqliteCanonicalRepository("sqlite://")
    registry = ContractRegistry(ROOT)
    service = SessionService(
        repository,
        CommitAuthority(repository, registry),
        registry,
        StaticSecretResolver("test-session-secret"),
        secret_ref="memory:local-dev",
    )
    identity = DeterministicAuthVerifier().verify("local:principal-auth")

    created = service.create_session(identity, idempotency_key="session-1", ttl_seconds=600)
    replayed = service.create_session(identity, idempotency_key="session-1", ttl_seconds=600)

    assert created["token"] == replayed["token"]
    assert replayed["replayed"] is True
    assert service.verify_session(created["token"]).principal_ref == "principal-auth"
    assert len(repository.query(record_types={"shadow.security.session"}, record_states={"active"})) == 1

    revoked = service.revoke(created["context"], idempotency_key="logout-1")
    assert revoked["session"]["typed_payload"]["lifecycle"] == "revoked"
    with pytest.raises(ShadowDomainError) as exc_info:
        service.verify_session(created["token"])
    assert exc_info.value.error.code == "shadow.auth.session-revoked"


def test_session_tampering_is_rejected() -> None:
    repository = SqliteCanonicalRepository("sqlite://")
    registry = ContractRegistry(ROOT)
    service = SessionService(
        repository,
        CommitAuthority(repository, registry),
        registry,
        StaticSecretResolver("test-session-secret"),
        secret_ref="memory:local-dev",
    )
    identity = DeterministicAuthVerifier().verify("local:principal-auth")
    token = service.create_session(identity, idempotency_key="session-tamper")["token"]
    with pytest.raises(ShadowDomainError) as exc_info:
        service.verify_session(token[:-1] + ("a" if token[-1] != "a" else "b"))
    assert exc_info.value.error.code == "shadow.auth.invalid-credential"


def test_local_dev_api_can_exchange_and_use_signed_session() -> None:
    client = TestClient(create_app("sqlite://"))
    config = client.get("/v1/auth/config")
    assert config.status_code == 200
    assert config.json()["local_dev"] is True

    created = client.post(
        "/v1/auth/session",
        headers={"Idempotency-Key": "api-session-1"},
        json={"credential": "local:principal-api", "use_cookie": False},
    )
    assert created.status_code == 201
    token = created.json()["token"]
    context = client.get("/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert context.status_code == 200
    assert context.json()["context"]["principal_ref"] == "principal-api"

    denied = client.get("/v1/auth/session")
    assert denied.status_code == 401

    logout = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "api-logout-1"},
    )
    assert logout.status_code == 202
    assert client.get("/v1/auth/session", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_signed_session_mode_does_not_exchange_raw_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHADOW_AUTH_MODE", "signed-session")
    monkeypatch.setenv("SHADOW_AUTH_SESSION_SECRET", "production-test-secret")
    client = TestClient(create_app("sqlite://"))

    exchange = client.post(
        "/v1/auth/session",
        headers={"Idempotency-Key": "signed-session-exchange"},
        json={"credential": "local:must-not-be-accepted", "use_cookie": False},
    )
    assert exchange.status_code == 409
    assert exchange.json()["code"] == "shadow.auth.exchange-unsupported"
    assert client.get("/v1/runtime").status_code == 401
