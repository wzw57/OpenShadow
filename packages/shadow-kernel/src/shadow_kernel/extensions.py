from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import ShadowDomainError, ShadowError
from .registry import ContractPack, ContractRegistry


@dataclass(frozen=True, slots=True)
class ExtensionDescriptor:
    """Small, declarative identity for a Profile or Runtime Extension."""

    extension_id: str
    version: str
    contract_packs: tuple[str, ...] = ()
    record_types: tuple[str, ...] = ()
    input_types: tuple[str, ...] = ()
    execution_target_kinds: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.extension_id.strip() or not self.version.strip():
            raise ValueError("Extension id and version must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "extension_id": self.extension_id,
            "version": self.version,
            "contract_packs": list(self.contract_packs),
            "record_types": list(self.record_types),
            "input_types": list(self.input_types),
            "execution_target_kinds": list(self.execution_target_kinds),
            "capabilities": list(self.capabilities),
        }


class Extension(Protocol):
    descriptor: ExtensionDescriptor


class ExtensionRegistry:
    """Composition-time registry for installed, vendor-neutral extensions."""

    def __init__(self, contract_registry: ContractRegistry | None = None) -> None:
        self.contract_registry = contract_registry
        self._extensions: dict[str, Extension] = {}
        self._record_owners: dict[str, str] = {}
        self._input_owners: dict[str, str] = {}
        self._target_owners: dict[str, str] = {}

    def register(
        self,
        extension: Extension,
        *,
        contract_packs: tuple[ContractPack, ...] | list[ContractPack] = (),
    ) -> ExtensionDescriptor:
        descriptor = extension.descriptor
        extension_id = descriptor.extension_id
        if extension_id in self._extensions:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.extension.duplicate",
                    category="conflict",
                    message=f"Extension id is already registered: {extension_id}.",
                    typed_details={"extension_id": extension_id},
                )
            )
        if self.contract_registry is not None:
            for pack in contract_packs:
                self.contract_registry.register_pack(pack)
            missing_packs = [
                pack_id
                for pack_id in descriptor.contract_packs
                if pack_id not in self.contract_registry.packs
            ]
            if missing_packs:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.extension.contract-pack-missing",
                        category="validation",
                        message=f"Extension {extension_id} references an unregistered contract pack.",
                        typed_details={"extension_id": extension_id, "pack_ids": missing_packs},
                    )
                )

        self._assert_unique("record type", descriptor.record_types, self._record_owners, extension_id)
        self._assert_unique("input type", descriptor.input_types, self._input_owners, extension_id)
        self._assert_unique(
            "execution target kind",
            descriptor.execution_target_kinds,
            self._target_owners,
            extension_id,
        )
        self._extensions[extension_id] = extension
        for record_type in descriptor.record_types:
            self._record_owners[record_type] = extension_id
        for input_type in descriptor.input_types:
            self._input_owners[input_type] = extension_id
        for target_kind in descriptor.execution_target_kinds:
            self._target_owners[target_kind] = extension_id
        return descriptor

    @staticmethod
    def _assert_unique(
        label: str, values: tuple[str, ...], owners: dict[str, str], extension_id: str
    ) -> None:
        collisions = [value for value in values if value in owners]
        if collisions:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.extension.namespace-conflict",
                    category="conflict",
                    message=f"Extension {label} is already owned by another extension.",
                    typed_details={"extension_id": extension_id, "values": collisions},
                )
            )

    def descriptor(self, extension_id: str) -> ExtensionDescriptor:
        extension = self._extensions.get(extension_id)
        if extension is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.extension.not-found",
                    category="validation",
                    message=f"Extension was not found: {extension_id}.",
                )
            )
        return extension.descriptor

    def extension_for_input(self, input_type: str) -> Extension:
        owner = self._input_owners.get(input_type)
        if owner is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.extension.input-unsupported",
                    category="unsupported",
                    message=f"No extension handles input type: {input_type}.",
                )
            )
        return self._extensions[owner]

    def extension_for_target(self, target_kind: str) -> Extension:
        owner = self._target_owners.get(target_kind)
        if owner is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.extension.target-unsupported",
                    category="unsupported",
                    message=f"No extension handles target kind: {target_kind}.",
                )
            )
        return self._extensions[owner]

    def descriptors(self) -> list[dict[str, Any]]:
        return [
            extension.descriptor.as_dict()
            for extension in sorted(self._extensions.values(), key=lambda item: item.descriptor.extension_id)
        ]


__all__ = ["Extension", "ExtensionDescriptor", "ExtensionRegistry"]
