"""A deliberately dependency-free example Profile Extension.

This fixture documents the smallest shape an extension should expose before the
production ExtensionRegistry exists.  It intentionally does not import
``shadow_application`` or ``shadow_server`` and it does not commit directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExampleProfileDescriptor:
    extension_id: str = "example.profile"
    version: str = "0.1.0"
    contract_packs: tuple[str, ...] = ("tests/fixtures/example-profile-contract-pack",)
    record_types: tuple[str, ...] = ("shadow.profile.example",)
    input_types: tuple[str, ...] = ("example.profile.create",)
    execution_target_kinds: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


class ExampleProfileExtension:
    """Minimal Profile shape for the R0 acceptance test."""

    descriptor = ExampleProfileDescriptor()

    def handle_input(
        self, payload: Mapping[str, Any], *, owner_ref: str, space_id: str
    ) -> dict[str, Any]:
        """Return a commit intent; the fixture never writes the repository itself."""
        if payload.get("input_type") != self.descriptor.input_types[0]:
            raise ValueError("Unsupported example Profile input type")
        return {
            "record_type": self.descriptor.record_types[0],
            "schema_ref": "https://schemas.openshadow.dev/contracts/example-profile/1.0.0#/$defs/ExamplePayload",
            "owner_ref": owner_ref,
            "space_id": space_id,
            "typed_payload": {"label": payload["label"]},
        }

    def register_routes(self, router: Any) -> None:
        """Optional route hook; generic server composition owns invocation."""
        del router


__all__ = ["ExampleProfileDescriptor", "ExampleProfileExtension"]
