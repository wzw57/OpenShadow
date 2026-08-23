from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag

from jsonschema import Draft202012Validator, RefResolver, SchemaError

from .errors import ShadowDomainError, ShadowError


@dataclass(frozen=True, slots=True)
class ContractPack:
    """A checked-in, offline contract pack.

    A pack is intentionally filesystem-backed.  The registry never resolves a
    schema reference by fetching a URL; callers must provide a local directory
    containing a manifest and its schema files.
    """

    pack_id: str
    root: Path
    manifest: Mapping[str, Any]

    @classmethod
    def from_directory(cls, directory: str | Path, *, pack_id: str | None = None) -> ContractPack:
        root = Path(directory).resolve()
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.pack-invalid",
                    category="validation",
                    message=f"Contract pack manifest was not found: {manifest_path}.",
                )
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.pack-invalid",
                    category="validation",
                    message=f"Contract pack manifest could not be read: {manifest_path}.",
                    typed_details={"reason": str(exc)},
                )
            ) from exc
        resolved_pack_id = str(pack_id or manifest.get("pack_id") or root.name).strip()
        if not resolved_pack_id or not isinstance(manifest.get("schemas"), list):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.pack-invalid",
                    category="validation",
                    message="A contract pack requires a non-empty pack id and schemas list.",
                )
            )
        return cls(pack_id=resolved_pack_id, root=root, manifest=manifest)

    def schema_path(self, relative_path: str) -> Path:
        root = self.root.resolve()
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.pack-invalid",
                    category="validation",
                    message=f"Contract path escapes pack root: {relative_path}.",
                    typed_details={"pack_id": self.pack_id, "path": relative_path},
                )
            ) from exc
        return path


class ContractRegistry:
    """Offline contract registry backed only by checked-in contract packs."""

    def __init__(self, repository_root: str | Path):
        self.repository_root = Path(repository_root)
        self.contract_root = self.repository_root / "contracts"
        core_pack = ContractPack.from_directory(self.contract_root, pack_id="core")
        # ``manifest`` remains a compatibility view for callers that used the
        # v0.1 single-manifest registry.
        self.manifest = dict(core_pack.manifest)
        self.schemas: dict[str, dict[str, Any]] = {}
        self.paths: dict[str, Path] = {}
        self._schema_digests: dict[str, str] = {}
        self._schema_pack_ids: dict[str, set[str]] = {}
        self.packs: dict[str, ContractPack] = {}
        self.register_pack(core_pack)

    def register_pack(self, pack: ContractPack | str | Path, *, pack_id: str | None = None) -> None:
        """Verify and register one local pack without network resolution.

        Identical schema bytes may be shared by multiple packs.  A schema id
        with different verified bytes is rejected before any part of that pack
        is added to the registry.
        """
        if not isinstance(pack, ContractPack):
            pack = ContractPack.from_directory(pack, pack_id=pack_id)
        existing_pack = self.packs.get(pack.pack_id)
        if existing_pack is not None:
            if existing_pack.root == pack.root and existing_pack.manifest == pack.manifest:
                return
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.pack-conflict",
                    category="conflict",
                    message=f"Contract pack id is already registered: {pack.pack_id}.",
                    typed_details={"pack_id": pack.pack_id},
                )
            )

        verified = self._verify_pack(pack)
        conflicts = [
            item
            for item in verified
            if item[0] in self._schema_digests and self._schema_digests[item[0]] != item[2]
        ]
        if conflicts:
            schema_id, _path, digest, _schema = conflicts[0]
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.schema-conflict",
                    category="conflict",
                    message=f"Incompatible duplicate schema id: {schema_id}.",
                    typed_details={
                        "schema_id": schema_id,
                        "existing_sha256": self._schema_digests[schema_id],
                        "incoming_sha256": digest,
                        "incoming_pack_id": pack.pack_id,
                    },
                )
            )

        self.packs[pack.pack_id] = pack
        for schema_id, path, digest, schema in verified:
            self._schema_pack_ids.setdefault(schema_id, set()).add(pack.pack_id)
            if schema_id not in self.schemas:
                self.schemas[schema_id] = schema
                self.paths[schema_id] = path
                self._schema_digests[schema_id] = digest

    def _verify_pack(self, pack: ContractPack) -> list[tuple[str, Path, str, dict[str, Any]]]:
        verified: list[tuple[str, Path, str, dict[str, Any]]] = []
        for entry in pack.manifest["schemas"]:
            if not isinstance(entry, dict) or not all(
                isinstance(entry.get(key), str) and entry[key] for key in ("schema_id", "path", "sha256")
            ):
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.pack-invalid",
                        category="validation",
                        message=f"Invalid schema manifest entry in pack {pack.pack_id}.",
                    )
                )
            schema_id = entry["schema_id"]
            path = pack.schema_path(entry["path"])
            try:
                raw = path.read_bytes()
            except OSError as exc:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.pack-invalid",
                        category="validation",
                        message=f"Contract schema could not be read for {schema_id}.",
                        typed_details={"pack_id": pack.pack_id, "path": str(path), "reason": str(exc)},
                    )
                ) from exc
            digest = hashlib.sha256(raw).hexdigest()
            if digest != entry["sha256"]:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.digest-mismatch",
                        category="validation",
                        message=f"Contract digest mismatch for {schema_id}.",
                        typed_details={
                            "pack_id": pack.pack_id,
                            "expected": entry["sha256"],
                            "actual": digest,
                        },
                    )
                )
            try:
                schema = json.loads(raw.decode("utf-8"))
                Draft202012Validator.check_schema(schema)
            except (UnicodeDecodeError, json.JSONDecodeError, SchemaError, TypeError, ValueError) as exc:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.pack-invalid",
                        category="validation",
                        message=f"Contract schema is invalid for {schema_id}.",
                        typed_details={"pack_id": pack.pack_id, "reason": str(exc)},
                    )
                ) from exc
            verified.append((schema_id, path, digest, schema))
        return verified

    def packs_for_schema(self, schema_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._schema_pack_ids.get(schema_id, set())))

    def schema(self, schema_ref: str) -> tuple[dict[str, Any], str]:
        base, fragment = urldefrag(schema_ref)
        if base not in self.schemas:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.contract.unknown-schema",
                    category="validation",
                    message=f"Unknown offline schema reference: {base}.",
                )
            )
        schema = self.schemas[base]
        if not fragment:
            return schema, base
        node: Any = schema
        for part in fragment.lstrip("/").split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node, base

    def validate(self, instance: Any, schema_ref: str) -> None:
        schema, base = self.schema(schema_ref)
        store = dict(self.schemas)
        resolver = RefResolver(base, self.schemas[base], store=store)
        Draft202012Validator(schema, resolver=resolver).validate(instance)

    def validate_envelope(self, envelope: dict[str, Any]) -> None:
        self.validate(
            envelope,
            "https://schemas.openshadow.dev/contracts/kernel/1.0.0#/$defs/CanonicalEnvelope",
        )
