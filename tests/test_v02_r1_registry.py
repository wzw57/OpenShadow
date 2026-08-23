from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from shadow_kernel.errors import ShadowDomainError
from shadow_kernel.extensions import ExtensionDescriptor, ExtensionRegistry
from shadow_kernel.registry import ContractPack, ContractRegistry

ROOT = Path(__file__).resolve().parents[1]


def _write_pack(
    root: Path,
    *,
    pack_id: str,
    schema_id: str,
    required_property: str = "value",
) -> ContractPack:
    schema_dir = root / "schemas"
    schema_dir.mkdir(parents=True)
    schema_path = schema_dir / "schema.json"
    schema = {
        "$id": schema_id,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {required_property: {"type": "string"}},
        "required": [required_property],
        "additionalProperties": False,
    }
    raw = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
    schema_path.write_bytes(raw)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "shadow.contract-registry.v1",
                "pack_id": pack_id,
                "schemas": [
                    {
                        "schema_id": schema_id,
                        "path": "schemas/schema.json",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return ContractPack.from_directory(root)


def test_core_registry_is_a_pack_and_extension_pack_is_offline(tmp_path: Path) -> None:
    registry = ContractRegistry(ROOT)
    assert registry.packs.keys() == {"core"}

    schema_id = "https://schemas.openshadow.dev/contracts/example/1.0.0"
    pack = _write_pack(tmp_path / "example-pack", pack_id="example-pack", schema_id=schema_id)
    registry.register_pack(pack)
    registry.validate({"value": "ok"}, schema_id)
    assert registry.packs_for_schema(schema_id) == ("example-pack",)


def test_identical_schema_id_bytes_are_shareable_but_incompatible_is_rejected(
    tmp_path: Path,
) -> None:
    schema_id = "https://schemas.openshadow.dev/contracts/example/shared/1.0.0"
    first = _write_pack(tmp_path / "first", pack_id="first", schema_id=schema_id)
    second = _write_pack(tmp_path / "second", pack_id="second", schema_id=schema_id)
    registry = ContractRegistry(ROOT)
    registry.register_pack(first)
    registry.register_pack(second)
    assert registry.packs_for_schema(schema_id) == ("first", "second")

    incompatible = _write_pack(
        tmp_path / "incompatible",
        pack_id="incompatible",
        schema_id=schema_id,
        required_property="different",
    )
    with pytest.raises(ShadowDomainError) as exc_info:
        registry.register_pack(incompatible)
    assert exc_info.value.error.code == "shadow.contract.schema-conflict"
    assert "incompatible" not in registry.packs


def test_pack_digest_and_path_traversal_are_rejected(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path / "tampered",
        pack_id="tampered",
        schema_id="https://schemas.openshadow.dev/contracts/example/tampered/1.0.0",
    )
    pack.schema_path("schemas/schema.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ShadowDomainError) as digest_error:
        ContractRegistry(ROOT).register_pack(pack)
    assert digest_error.value.error.code == "shadow.contract.digest-mismatch"

    escaping = tmp_path / "escaping"
    escaping.mkdir()
    (escaping / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "escaping",
                "schemas": [
                    {
                        "schema_id": "https://schemas.openshadow.dev/contracts/example/escape/1.0.0",
                        "path": "../outside.json",
                        "sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ShadowDomainError) as path_error:
        ContractRegistry(ROOT).register_pack(ContractPack.from_directory(escaping))
    assert path_error.value.error.code == "shadow.contract.pack-invalid"


@dataclass
class _ExampleExtension:
    descriptor: ExtensionDescriptor


def test_extension_registry_owns_namespaces_and_requires_registered_packs(tmp_path: Path) -> None:
    registry = ContractRegistry(ROOT)
    pack = _write_pack(
        tmp_path / "profile-pack",
        pack_id="profile-pack",
        schema_id="https://schemas.openshadow.dev/contracts/example/profile/1.0.0",
    )
    extensions = ExtensionRegistry(registry)
    extension = _ExampleExtension(
        ExtensionDescriptor(
            extension_id="example.profile",
            version="0.1.0",
            contract_packs=("profile-pack",),
            record_types=("shadow.profile.example",),
            input_types=("example.profile.create",),
            capabilities=("example.read",),
        )
    )
    extensions.register(extension, contract_packs=[pack])
    assert extensions.extension_for_input("example.profile.create") is extension
    assert extensions.descriptors()[0]["extension_id"] == "example.profile"

    with pytest.raises(ShadowDomainError) as duplicate:
        extensions.register(extension, contract_packs=[pack])
    assert duplicate.value.error.code == "shadow.extension.duplicate"

    missing = _ExampleExtension(
        ExtensionDescriptor(
            extension_id="example.missing",
            version="0.1.0",
            contract_packs=("not-installed",),
            record_types=("shadow.profile.missing",),
        )
    )
    with pytest.raises(ShadowDomainError) as missing_error:
        extensions.register(missing)
    assert missing_error.value.error.code == "shadow.extension.contract-pack-missing"
