from __future__ import annotations

from pathlib import Path


def test_web_ui_does_not_branch_on_runtime_vendor() -> None:
    source = (Path(__file__).parents[1] / "apps" / "shadow-web" / "src" / "App.tsx").read_text(
        encoding="utf-8"
    )

    assert "Hermes" not in source
    assert "Ollama" not in source
    assert "DeepSeek" not in source
    assert "Deterministic" not in source
