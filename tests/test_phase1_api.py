from __future__ import annotations

from fastapi.testclient import TestClient
from shadow_server.app import create_app


def _turn() -> dict:
    return {
        "submission_id": "submission-1",
        "message_type": "shadow.message.user",
        "content_blocks": [
            {
                "block_type": "shadow.content.text",
                "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
                "typed_content": {"text": "hello"},
            }
        ],
        "turn_mode": "new",
    }


def test_personal_shadow_loop_and_replay() -> None:
    client = TestClient(create_app("sqlite://"))
    assert client.get("/healthz").json() == {"status": "healthy", "durable": True}
    created = client.post(
        "/v1/conversations", json={"title": "Test"}, headers={"Idempotency-Key": "conversation-1"}
    )
    assert created.status_code == 201
    conversation_id = created.json()["record"]["record_id"]

    first = client.post(
        f"/v1/conversations/{conversation_id}/turns",
        json=_turn(),
        headers={"Idempotency-Key": "turn-1"},
    )
    replay = client.post(
        f"/v1/conversations/{conversation_id}/turns",
        json=_turn(),
        headers={"Idempotency-Key": "turn-1"},
    )
    assert first.status_code == replay.status_code == 202
    assert first.json()["replayed"] is False
    assert replay.json()["replayed"] is True
    assert len(client.get(f"/v1/conversations/{conversation_id}/messages").json()["records"]) == 2

    run_id = first.json()["root_run_ref"]["record_id"]
    run = client.get(f"/v1/runs/{run_id}").json()["record"]["typed_payload"]
    assert run["lifecycle"] == "completed"
    events = client.get(f"/v1/runs/{run_id}/events").text
    assert "shadow.run.started" in events and "shadow.run.completed" in events


def test_store_outage_does_not_claim_durable_success() -> None:
    app = create_app("sqlite://")
    client = TestClient(app)
    created = client.post(
        "/v1/conversations", json={}, headers={"Idempotency-Key": "conversation-2"}
    )
    conversation_id = created.json()["record"]["record_id"]
    app.state.repository.set_available(False)
    response = client.post(
        f"/v1/conversations/{conversation_id}/turns",
        json=_turn(),
        headers={"Idempotency-Key": "turn-2"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "shadow.repository.unavailable"


def test_memory_candidate_is_committed_only_through_authority() -> None:
    client = TestClient(create_app("sqlite://"))
    response = client.post(
        "/v1/memories",
        json={
            "memory_kind": "shadow.memory.preference",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "concise updates"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
            "source_dependency": "independent",
        },
        headers={"Idempotency-Key": "memory-1"},
    )
    assert response.status_code == 201
    record = response.json()["record"]
    assert record["record_type"] == "shadow.profile.memory"
    assert record["typed_payload"]["memory_state"] == "active"
    assert client.get("/v1/memories").json()["records"][0]["record_id"] == record["record_id"]


def test_invalid_memory_candidate_is_a_structured_validation_error() -> None:
    client = TestClient(create_app("sqlite://"))
    response = client.post(
        "/v1/memories",
        json={
            "memory_kind": "not-namespaced",
            "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
            "typed_content": {"text": "invalid"},
            "applicability_scope": {"scope_kind": "shadow.scope.personal", "scope_refs": []},
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "shadow.memory.candidate-invalid"
