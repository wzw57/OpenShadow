from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag

from jsonschema import Draft202012Validator, RefResolver

from .errors import ShadowDomainError, ShadowError


class ContractRegistry:
    """Offline contract registry backed only by checked-in files."""

    def __init__(self, repository_root: str | Path):
        self.repository_root = Path(repository_root)
        self.contract_root = self.repository_root / "contracts"
        manifest_path = self.contract_root / "manifest.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.schemas: dict[str, dict[str, Any]] = {}
        self.paths: dict[str, Path] = {}
        self._load_and_verify()

    def _load_and_verify(self) -> None:
        for entry in self.manifest["schemas"]:
            schema_id = entry["schema_id"]
            path = self.contract_root / entry["path"]
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != entry["sha256"]:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.contract.digest-mismatch",
                        category="validation",
                        message=f"Contract digest mismatch for {schema_id}.",
                        typed_details={"expected": entry["sha256"], "actual": digest},
                    )
                )
            schema = json.loads(raw.decode("utf-8"))
            Draft202012Validator.check_schema(schema)
            self.schemas[schema_id] = schema
            self.paths[schema_id] = path

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
