from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from shadow_application.erase import PhysicalEraseRequest
from shadow_kernel.errors import ShadowDomainError, ShadowError


@dataclass(slots=True)
class DeterministicErasureAdapter:
    """Test adapter that proves erase ordering without external side effects."""

    state: Literal["ready", "unavailable"] = "ready"
    finalize_state: Literal["ready", "unavailable"] = "ready"
    calls: list[str] = field(default_factory=list)

    def _require(self, step: str, state: str = "ready") -> None:
        if state == "unavailable":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.erasure.adapter-unavailable",
                    category="unavailable",
                    message=f"Deterministic Erasure Adapter {step} step is unavailable.",
                    retryable=True,
                )
            )
        self.calls.append(step)

    def quiesce(self, request: PhysicalEraseRequest, record: dict) -> None:
        del request, record
        self._require("quiesce", self.state)

    def erase(self, request: PhysicalEraseRequest, record: dict) -> None:
        del request, record
        self._require("erase", self.state)

    def finalize(self, request: PhysicalEraseRequest, tombstone: dict) -> None:
        del request, tombstone
        self._require("finalize", self.finalize_state)


__all__ = ["DeterministicErasureAdapter"]
