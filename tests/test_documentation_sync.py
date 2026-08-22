from __future__ import annotations

from pathlib import Path

from shadow_server.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_phase2_status_and_adr_are_delivered() -> None:
    gate = _read("docs/phase2-design-gate.md")
    adr = _read("docs/adr/0005-phase2-memory-lifecycle.md")
    status = _read("docs/phase2-memory-lifecycle-status.md")
    roadmap = _read("docs/roadmap.md")

    assert "Accepted / Phase 2 首个切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "PR [#8]" in status
    assert "合并到 `main`" in status
    assert "合并到 `main`" in roadmap
    assert "phase2/memory-lifecycle` 分支实现" not in roadmap


def test_next_phase2_slice_is_accepted_before_implementation() -> None:
    gate = _read("docs/phase2-recall-maintenance-design-gate.md")
    adr = _read("docs/adr/0006-phase2-recall-maintenance.md")
    status = _read("docs/phase2-memory-lifecycle-status.md")

    assert "Accepted / Phase 2 第二切片获准实现" in gate
    assert "- Status: Accepted" in adr
    assert "当前为 Accepted；实现分支将从最新 `main` 创建" in status
    assert "不新增 HTTP 路由" in gate
    assert "不新增数据库表" in gate


def test_phase2_service_surface_is_documented() -> None:
    source = _read("packages/shadow-application/src/shadow_application/memory.py")
    status = _read("docs/phase2-memory-lifecycle-status.md")

    for method_name in (
        "propose_correction",
        "commit_correction",
        "propose_merge",
        "commit_merge",
        "logical_delete",
    ):
        assert f"def {method_name}(" in source

    for documented_name in (
        "MemoryService.propose_correction",
        "MemoryService.commit_correction",
        "propose_merge` / `commit_merge",
        "logical_delete",
    ):
        assert documented_name in status


def test_phase2_http_contract_matches_app_and_static_openapi() -> None:
    app_source = _read("apps/shadow-server/shadow_server/app.py")
    openapi_source = _read("contracts/openapi/openapi.yaml")
    status = _read("docs/phase2-memory-lifecycle-status.md")
    schema = create_app("sqlite://").openapi()
    required_headers = {
        "Expected-Version",
        "idempotency-key",
        "X-Principal-Ref",
        "X-Space-Id",
    }

    for path, method in (
        ("/v1/memories/{memory_id}/corrections", "post"),
        ("/v1/memories/{memory_id}", "delete"),
    ):
        assert path in schema["paths"]
        params = {
            parameter["name"]: parameter
            for parameter in schema["paths"][path][method]["parameters"]
            if parameter["in"] == "header"
        }
        assert required_headers <= params.keys()
        assert all(params[name]["required"] for name in required_headers)
        assert path in openapi_source

    for header in ("Expected-Version", "X-Principal-Ref", "X-Space-Id"):
        assert f"name: {header}" in openapi_source
    assert "name: Idempotency-Key" in openapi_source
    assert "/v1/memories/merges" not in app_source
    assert "/v1/memories/merges" not in openapi_source
    assert "merge 保持 Application / Contract" in status
