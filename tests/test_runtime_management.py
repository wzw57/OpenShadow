from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from shadow_application import RuntimeProfile, RuntimeSupervisor
from shadow_codex import CodexAgentRuntimeAdapter
from shadow_kernel.errors import ShadowDomainError
from shadow_server.app import create_app


def test_runtime_management_api_lists_profiles_and_controls_deterministic() -> None:
    client = TestClient(create_app("sqlite://"))
    overview = client.get("/v1/management/overview")
    assert overview.status_code == 200
    assert overview.json()["active_runtime_id"] == "deterministic"
    assert {item["runtime_id"] for item in overview.json()["runtimes"]} == {"deterministic", "hermes", "codex"}

    started = client.post(
        "/v1/runtime/instances/deterministic/start",
        headers={"Idempotency-Key": "runtime-start"},
    )
    assert started.status_code == 202
    assert started.json()["runtime"]["state"]["health"] == "healthy"

    replay = client.post(
        "/v1/runtime/instances/deterministic/start",
        headers={"Idempotency-Key": "runtime-start"},
    )
    assert replay.status_code == 202
    assert replay.json()["runtime"]["replayed"] is True

    selected = client.post(
        "/v1/runtime/instances/deterministic/select",
        headers={"Idempotency-Key": "runtime-select"},
    )
    assert selected.status_code == 200
    assert selected.json()["runtime"]["active"] is True

    disabled = client.post(
        "/v1/runtime/instances/hermes/start",
        headers={"Idempotency-Key": "runtime-codex-start"},
    )
    assert disabled.status_code == 422
    assert disabled.json()["code"] == "shadow.runtime.disabled"


def test_runtime_supervisor_process_lifecycle_and_selection_guard(tmp_path: Path) -> None:
    profile = RuntimeProfile(
        runtime_id="fake",
        display_name="Fake Runtime",
        adapter_factory="shadow_adapters:create_runtime_adapter",
        target_kind="shadow.deterministic-runner",
        enabled=True,
        launch_command=(sys.executable, "-c", "import time; time.sleep(30)"),
        launch_cwd=str(tmp_path),
    )
    supervisor = RuntimeSupervisor([profile], active_runtime_id="fake")
    started = supervisor.start("fake", "fake-start")
    assert started["state"]["lifecycle"] == "healthy"
    assert started["state"]["pid"]
    assert supervisor.stop("fake", "fake-stop")["state"]["lifecycle"] == "stopped"

    guarded = RuntimeSupervisor([profile], active_runtime_id="fake", selection_guard=lambda: True)
    guarded.start("fake", "guarded-start")
    try:
        guarded.select("fake", "guarded-select")
    except ShadowDomainError as exc:
        assert exc.error.code == "shadow.runtime.selection-conflict"
    else:
        raise AssertionError("selection should be blocked while a Run is executing")
    guarded.stop("fake", "guarded-stop")


def test_codex_adapter_parses_jsonl_without_invoking_codex_internals() -> None:
    events = CodexAgentRuntimeAdapter._parse_events(
        json.dumps({"type": "thread.started", "thread_id": "thread-1"})
        + "\n"
        + json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "OK"}}),
        "codex:test",
    )
    assert CodexAgentRuntimeAdapter._extract_text(events) == "OK"
    assert CodexAgentRuntimeAdapter._extract_session(events) == "thread-1"
