from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository, create_canonical_repository


def test_store_factory_keeps_sqlite_as_explicit_local_profile() -> None:
    repository = create_canonical_repository("sqlite://")
    assert isinstance(repository, SqliteCanonicalRepository)
    assert repository.health()["durable"] is True


def test_store_factory_rejects_unknown_backend_without_fallback() -> None:
    with pytest.raises(ValueError, match="Unsupported SHADOW_DATABASE_URL backend"):
        create_canonical_repository("mysql+pymysql://user:pass@localhost/shadow")


def test_app_does_not_silently_fallback_when_store_url_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHADOW_DATABASE_URL", "mysql+pymysql://user:pass@localhost/shadow")
    with pytest.raises(ValueError, match="Unsupported SHADOW_DATABASE_URL backend"):
        create_app()


def test_store_readiness_reflects_unavailable_repository() -> None:
    client = TestClient(create_app("sqlite://"))
    client.app.state.repository.set_available(False)
    assert client.get("/healthz").json() == {"status": "unavailable", "durable": False}
    assert client.get("/readyz").status_code == 503
