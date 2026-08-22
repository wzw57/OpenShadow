from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from shadow_hermes import HermesAgentRuntimeAdapter
from shadow_kernel.errors import ShadowDomainError
from shadow_server.app import create_app


class _HermesHandler(BaseHTTPRequestHandler):
    response_mode: ClassVar[str] = "success"
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "healthy"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        self.requests.append({"path": self.path, "body": body, "headers": dict(self.headers)})
        if self.response_mode == "unavailable":
            self._send(503, {"error": "down"})
        elif self.response_mode == "invalid":
            self._send(200, {"unexpected": True})
        else:
            self._send(
                200,
                {
                    "id": "chatcmpl-hermes-test",
                    "choices": [{"message": {"role": "assistant", "content": "Hello from Hermes"}}],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
                },
            )

    def _send(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args: Any) -> None:
        return


@pytest.fixture()
def hermes_server() -> Any:
    _HermesHandler.response_mode = "success"
    _HermesHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HermesHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_hermes_adapter_round_trip_and_descriptor(hermes_server: Any) -> None:
    port = hermes_server.server_address[1]
    adapter = HermesAgentRuntimeAdapter(
        base_url=f"http://127.0.0.1:{port}/v1",
        api_key="local-test-key",
        session_id="session-shadow-test",
    )

    descriptor = adapter.describe()
    assert descriptor["supported_target_kinds"] == ["shadow.agent-runtime"]
    assert descriptor["capabilities"] == []

    result = adapter.execute("hello")

    assert result.text == "Hello from Hermes"
    assert result.usage == {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}
    assert result.execution_ref == "chatcmpl-hermes-test"
    assert adapter.events(result.execution_ref) == [
        {"cursor": "1", "event_type": "runtime.completed", "execution_ref": result.execution_ref}
    ]
    request = _HermesHandler.requests[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["body"]["stream"] is False
    assert request["headers"]["Authorization"] == "Bearer local-test-key"
    assert request["headers"]["X-Hermes-Session-Id"] == "session-shadow-test"
    assert adapter.health() == {"status": "healthy"}


def test_hermes_adapter_maps_unavailable(hermes_server: Any) -> None:
    _HermesHandler.response_mode = "unavailable"
    port = hermes_server.server_address[1]
    adapter = HermesAgentRuntimeAdapter(base_url=f"http://127.0.0.1:{port}/v1")

    with pytest.raises(ShadowDomainError) as exc_info:
        adapter.execute("hello")

    assert exc_info.value.error.code == "shadow.runtime.http-error"
    assert exc_info.value.error.category == "unavailable"
    assert exc_info.value.error.retryable is True


def test_hermes_adapter_rejects_protocol_mismatch(hermes_server: Any) -> None:
    _HermesHandler.response_mode = "invalid"
    port = hermes_server.server_address[1]
    adapter = HermesAgentRuntimeAdapter(base_url=f"http://127.0.0.1:{port}/v1")

    with pytest.raises(ShadowDomainError) as exc_info:
        adapter.execute("hello")

    assert exc_info.value.error.code == "shadow.runtime.protocol-incompatible"
    assert exc_info.value.error.category == "incompatible"


def test_hermes_adapter_wires_through_shadow_conversation(hermes_server: Any) -> None:
    port = hermes_server.server_address[1]
    adapter = HermesAgentRuntimeAdapter(
        base_url=f"http://127.0.0.1:{port}/v1", api_key="local-test-key"
    )
    client = TestClient(create_app(database_url="sqlite://", runtime_adapter=adapter))
    headers = {
        "X-Principal-Ref": "principal-local",
        "X-Space-Id": "space-personal",
        "Idempotency-Key": "hermes-conversation",
    }
    conversation_response = client.post(
        "/v1/conversations", json={"title": "Hermes"}, headers=headers
    )
    conversation_id = conversation_response.json()["record"]["record_id"]

    turn_response = client.post(
        f"/v1/conversations/{conversation_id}/turns",
        json={
            "submission_id": "hermes-turn",
            "content_blocks": [
                {
                    "block_type": "shadow.content.text",
                    "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0",
                    "typed_content": {"text": "hello"},
                }
            ],
        },
        headers=headers,
    )

    assert turn_response.status_code == 202
    run_id = turn_response.json()["root_run_ref"]["record_id"]
    run = client.get(f"/v1/runs/{run_id}").json()["record"]
    attempt_id = run["typed_payload"]["active_attempt_ref"]["record_id"]
    attempt = client.get(f"/v1/requests/{attempt_id}")
    assert attempt.status_code == 200
    assert attempt.json()["record"]["typed_payload"]["execution_ref"] == "chatcmpl-hermes-test"
