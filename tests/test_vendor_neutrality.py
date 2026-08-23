from __future__ import annotations

from pathlib import Path

from shadow_hermes import HermesAgentRuntimeAdapter
from shadow_server.app import _runtime_from_environment


def test_public_layers_do_not_name_concrete_vendors() -> None:
    root = Path(__file__).parents[1]
    public_roots = [
        root / "packages" / "shadow-kernel" / "src",
        root / "packages" / "shadow-application" / "src",
        root / "apps" / "shadow-server" / "shadow_server",
        root / "apps" / "shadow-web" / "src",
        root / "contracts" / "openapi",
    ]
    forbidden = ("Hermes", "Ollama", "DeepSeek", "vLLM", "llama.cpp")
    violations: list[str] = []
    for source_root in public_roots:
        for path in source_root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".yaml", ".json"}:
                text = path.read_text(encoding="utf-8")
                for vendor in forbidden:
                    if vendor in text:
                        violations.append(f"{path.relative_to(root)}: {vendor}")
    assert not violations, "Vendor coupling leaked into public layers: " + ", ".join(violations)


def test_server_loads_runtime_through_generic_factory_reference(monkeypatch) -> None:
    monkeypatch.setenv("SHADOW_RUNTIME_ADAPTER_FACTORY", "shadow_hermes:create_runtime_adapter")
    monkeypatch.delenv("SHADOW_RUNTIME_KIND", raising=False)

    adapter = _runtime_from_environment()

    assert isinstance(adapter, HermesAgentRuntimeAdapter)
