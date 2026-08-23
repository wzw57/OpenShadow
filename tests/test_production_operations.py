from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from shadow_server.app import create_app


def test_correlation_id_is_reused_and_metrics_are_low_cardinality() -> None:
    client = TestClient(create_app("sqlite://"))
    response = client.get("/healthz", headers={"X-Correlation-Id": "corr-test-1"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-test-1"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "shadow_http_requests_total" in metrics.text
    assert "principal" not in metrics.text
    assert "token" not in metrics.text


def test_telemetry_logs_only_route_status_and_correlation(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="shadow.http")
    client = TestClient(create_app("sqlite://"))
    client.get("/healthz", headers={"X-Correlation-Id": "corr-log-1"})
    record = next(item for item in caplog.records if item.name == "shadow.http")
    assert record.route == "/healthz"
    assert record.status == 200
    assert record.correlation_id == "corr-log-1"
    assert not hasattr(record, "credential")


def test_oidc_mode_fails_fast_when_trust_configuration_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHADOW_AUTH_MODE", "oidc")
    monkeypatch.setenv("SHADOW_AUTH_SESSION_SECRET", "test-secret")
    for name in ("SHADOW_OIDC_ISSUER", "SHADOW_OIDC_AUDIENCE", "SHADOW_OIDC_JWKS_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="OIDC auth mode requires"):
        create_app("sqlite://")
