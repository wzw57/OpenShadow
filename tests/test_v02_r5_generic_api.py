from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from shadow_server.app import create_app
from shadow_store import SqliteCanonicalRepository


def test_generic_extensions_records_and_inputs_use_owner_space_boundary(tmp_path: Path) -> None:
    app = create_app(f"sqlite:///{(tmp_path / 'generic.db').as_posix()}")
    client = TestClient(app)
    headers = {
        "X-Principal-Ref": "principal-generic",
        "X-Space-Id": "space-generic",
        "Idempotency-Key": "generic-state-input",
    }
    extensions = client.get("/v1/extensions", headers=headers)
    assert extensions.status_code == 200
    assert "shadow.profile.state" in {
        item["extension_id"] for item in extensions.json()["extensions"]
    }

    submitted = client.post(
        "/v1/inputs",
        headers=headers,
        json={
            "input_type": "shadow.state-proposal",
            "proposed_operation": "create",
            "state_key": "presence.generic",
            "value_schema_ref": "https://schemas.openshadow.dev/examples/presence/1.0.0",
            "proposed_value": {"present": True},
            "observed_at": "2026-08-22T08:00:00Z",
            "expires_at": "2099-08-22T00:00:00Z",
            "source_status": "available",
        },
    )
    assert submitted.status_code == 202, submitted.text
    record_id = submitted.json()["record"]["record_id"]
    queried = client.get(f"/v1/records/{record_id}", headers=headers)
    assert queried.status_code == 200
    assert queried.json()["record"]["record_id"] == record_id
    listed = client.get(
        "/v1/records",
        headers={key: value for key, value in headers.items() if key != "Idempotency-Key"},
        params={"record_type": "shadow.proposal"},
    )
    assert listed.status_code == 200
    assert any(item["record_id"] == record_id for item in listed.json()["records"])
    foreign = client.get(
        f"/v1/records/{record_id}",
        headers={"X-Principal-Ref": "principal-other", "X-Space-Id": "space-generic"},
    )
    assert foreign.status_code == 404


def test_store_factory_is_injected_at_composition_boundary() -> None:
    calls: list[str] = []

    def factory(database_url: str):
        calls.append(database_url)
        return SqliteCanonicalRepository("sqlite://")

    app = create_app("sqlite://", store_factory=factory)
    assert calls == ["sqlite://"]
    assert app.state.repository.available is True


def test_generic_api_routes_are_synchronized_with_static_openapi() -> None:
    app = create_app("sqlite://")
    runtime_schema = app.openapi()
    static_schema = (Path(__file__).resolve().parents[1] / "contracts/openapi/openapi.yaml").read_text(encoding="utf-8")

    for path, method in (
        ("/v1/extensions", "get"),
        ("/v1/records", "get"),
        ("/v1/records/{record_id}", "get"),
        ("/v1/inputs", "post"),
    ):
        assert path in runtime_schema["paths"]
        assert method in runtime_schema["paths"][path]
        assert path in static_schema

    list_parameters = runtime_schema["paths"]["/v1/records"]["get"]["parameters"]
    assert {item["name"] for item in list_parameters} >= {
        "X-Principal-Ref",
        "X-Space-Id",
        "record_type",
        "record_state",
        "limit",
    }
    input_schema = runtime_schema["paths"]["/v1/inputs"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert input_schema["type"] == "object"
    assert "GenericInputPayload" in static_schema
