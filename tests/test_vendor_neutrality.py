from __future__ import annotations

from pathlib import Path


def test_public_layers_do_not_name_concrete_vendors() -> None:
    root = Path(__file__).parents[1]
    public_roots = [
        root / "packages" / "shadow-kernel" / "src",
        root / "packages" / "shadow-application" / "src",
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
