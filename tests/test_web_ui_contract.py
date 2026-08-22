from __future__ import annotations

from fastapi.testclient import TestClient
from shadow_server.app import create_app


def test_runtime_status_is_non_secret_and_describes_deterministic_adapter() -> None:
    client = TestClient(create_app(database_url="sqlite://"))

    response = client.get("/v1/runtime")

    assert response.status_code == 200
    body = response.json()["runtime"]
    assert body["status"] == "configured"
    assert body["target_kind"] == "shadow.deterministic-runner"
    assert body["descriptor"]["descriptor_id"] == "shadow.adapter.deterministic"
    assert "api_key" not in response.text.lower()
