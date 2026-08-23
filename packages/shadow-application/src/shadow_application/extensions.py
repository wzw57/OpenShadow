from __future__ import annotations

from dataclasses import dataclass

from shadow_kernel.extensions import ExtensionDescriptor, ExtensionRegistry


@dataclass(frozen=True, slots=True)
class BuiltInExtension:
    descriptor: ExtensionDescriptor


def register_builtin_extensions(registry: ExtensionRegistry) -> None:
    """Register the reference Profile/Runtime descriptors at composition time."""
    descriptors = (
        ExtensionDescriptor(
            extension_id="shadow.profile.conversation",
            version="1.0.0",
            record_types=("shadow.profile.conversation", "shadow.profile.message"),
            input_types=("shadow.input.conversation-turn",),
        ),
        ExtensionDescriptor(
            extension_id="shadow.profile.memory",
            version="1.0.0",
            record_types=("shadow.profile.memory",),
        ),
        ExtensionDescriptor(
            extension_id="shadow.profile.state",
            version="1.0.0",
            record_types=("shadow.profile.state",),
            input_types=("shadow.state-proposal",),
        ),
        ExtensionDescriptor(
            extension_id="shadow.profile.task",
            version="1.0.0",
            record_types=("shadow.profile.task", "shadow.profile.checkpoint"),
            input_types=("shadow.durable-task-proposal",),
        ),
        ExtensionDescriptor(
            extension_id="shadow.profile.action",
            version="1.0.0",
            record_types=(
                "shadow.profile.action",
                "shadow.profile.action-approval",
                "shadow.profile.action-result",
                "shadow.profile.action-reconciliation",
            ),
            input_types=("shadow.action-proposal", "shadow.action-approval-proposal"),
        ),
    )
    for descriptor in descriptors:
        registry.register(BuiltInExtension(descriptor))


__all__ = ["BuiltInExtension", "register_builtin_extensions"]
