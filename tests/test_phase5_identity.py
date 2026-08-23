from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from shadow_server.app import create_app


def _headers(principal: str, space: str = "space-personal", key: str | None = None) -> dict[str, str]:
    value = {"X-Principal-Ref": principal, "X-Space-Id": space}
    if key:
        value["Idempotency-Key"] = key
    return value


def test_space_invitation_acceptance_and_acl() -> None:
    client = TestClient(create_app(database_url="sqlite://"))
    owner = _headers("principal-owner")
    created = client.post(
        "/v1/spaces",
        json={"space_id": "space-shared", "display_name": "Shared"},
        headers={**owner, "Idempotency-Key": "space-create"},
    )
    assert created.status_code == 201, created.text
    space_replay = client.post(
        "/v1/spaces",
        json={"space_id": "space-shared", "display_name": "Shared"},
        headers={**owner, "Idempotency-Key": "space-create"},
    )
    assert space_replay.status_code == 201
    assert space_replay.json()["replayed"] is True
    invitation = client.post(
        "/v1/spaces/space-shared/invitations",
        json={
            "invitee_ref": "principal-viewer",
            "role": "viewer",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        },
        headers={**owner, "X-Space-Id": "space-shared", "Idempotency-Key": "invite-1"},
    )
    assert invitation.status_code == 202, invitation.text
    invitation_body = invitation.json()
    accepted = client.post(
        f"/v1/invitations/{invitation_body['invitation']['record_id']}/accept",
        json={"invitation_token": invitation_body["invitation_token"]},
        headers={**_headers("principal-viewer", "space-shared"), "Idempotency-Key": "accept-1"},
    )
    assert accepted.status_code == 202, accepted.text
    accepted_replay = client.post(
        f"/v1/invitations/{invitation_body['invitation']['record_id']}/accept",
        json={"invitation_token": invitation_body["invitation_token"]},
        headers={**_headers("principal-viewer", "space-shared"), "Idempotency-Key": "accept-1"},
    )
    assert accepted_replay.status_code == 202
    assert accepted_replay.json()["replayed"] is True
    owner_conversation = client.post(
        "/v1/conversations",
        json={"title": "shared owner"},
        headers={**owner, "X-Space-Id": "space-shared", "Idempotency-Key": "owner-shared-conversation"},
    )
    assert owner_conversation.status_code == 201
    visible = client.get(
        "/v1/conversations", headers=_headers("principal-viewer", "space-shared")
    )
    assert visible.status_code == 200
    assert visible.json()["records"][0]["space_id"] == "space-shared"
    members = client.get(
        "/v1/spaces/space-shared/members", headers=_headers("principal-viewer", "space-shared")
    )
    assert members.status_code == 200
    assert {item["typed_payload"]["principal_ref"] for item in members.json()["records"]} == {
        "principal-owner",
        "principal-viewer",
    }
    denied = client.post(
        "/v1/conversations",
        json={"title": "should fail"},
        headers={**_headers("principal-viewer", "space-shared"), "Idempotency-Key": "viewer-write"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "shadow.space.membership-denied"


def test_editor_can_create_in_shared_space_and_other_space_is_hidden() -> None:
    client = TestClient(create_app(database_url="sqlite://"))
    owner = _headers("principal-owner")
    client.post(
        "/v1/spaces",
        json={"space_id": "space-edit", "display_name": "Edit"},
        headers={**owner, "Idempotency-Key": "space-edit-create"},
    )
    invitation = client.post(
        "/v1/spaces/space-edit/invitations",
        json={
            "invitee_ref": "principal-editor",
            "role": "editor",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        },
        headers={**owner, "X-Space-Id": "space-edit", "Idempotency-Key": "invite-editor"},
    ).json()
    client.post(
        f"/v1/invitations/{invitation['invitation']['record_id']}/accept",
        json={"invitation_token": invitation["invitation_token"]},
        headers={**_headers("principal-editor", "space-edit"), "Idempotency-Key": "accept-editor"},
    )
    created = client.post(
        "/v1/conversations",
        json={"title": "editor conversation"},
        headers={**_headers("principal-editor", "space-edit"), "Idempotency-Key": "editor-conversation"},
    )
    assert created.status_code == 201, created.text
    spaces = client.get("/v1/spaces", headers=_headers("principal-editor"))
    assert spaces.status_code == 200
    assert {item["record_id"] for item in spaces.json()["records"]} == {"space-edit"}
    hidden = client.get("/v1/spaces/space-personal", headers=_headers("principal-editor"))
    assert hidden.status_code == 403


def test_endpoint_pair_and_revoke_blocks_endpoint_context() -> None:
    client = TestClient(create_app(database_url="sqlite://"))
    headers = _headers("principal-local")
    paired = client.post(
        "/v1/endpoints/pair",
        json={"endpoint_ref": "endpoint-test", "label": "Test", "capabilities": ["shadow.endpoint.text"]},
        headers={**headers, "Idempotency-Key": "pair-1"},
    )
    assert paired.status_code == 201, paired.text
    replayed = client.post(
        "/v1/endpoints/pair",
        json={"endpoint_ref": "endpoint-test", "label": "Test", "capabilities": ["shadow.endpoint.text"]},
        headers={**headers, "Idempotency-Key": "pair-1"},
    )
    assert replayed.status_code == 201
    assert replayed.json()["replayed"] is True
    assert replayed.json()["endpoint"]["version"] == paired.json()["endpoint"]["version"]
    endpoint = paired.json()["endpoint"]
    revoked = client.post(
        "/v1/endpoints/endpoint-test/revoke",
        headers={**headers, "Expected-Version": str(endpoint["version"]), "Idempotency-Key": "revoke-1"},
    )
    assert revoked.status_code == 202, revoked.text
    rejected = client.post(
        "/v1/conversations/local/turns",
        json={"submission_id": "turn-1", "content_blocks": [{"block_type": "shadow.content.text", "content_schema_ref": "https://schemas.openshadow.dev/content/text/1.0.0", "typed_content": {"text": "hello"}}]},
        headers={**headers, "X-Endpoint-Ref": "endpoint-test", "Idempotency-Key": "turn-1"},
    )
    assert rejected.status_code in {403, 404}
