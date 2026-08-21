from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .ids import new_id

ErrorCategory = Literal[
    "validation",
    "incompatible",
    "unauthorized",
    "conflict",
    "unsupported",
    "unavailable",
    "timeout",
    "rate-limited",
    "internal",
]


@dataclass(slots=True)
class ShadowError:
    code: str
    category: ErrorCategory
    message: str
    retryable: bool = False
    typed_details: Any | None = None
    error_id: str = ""

    def __post_init__(self) -> None:
        if not self.error_id:
            self.error_id = new_id("error")

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error_id": self.error_id,
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.typed_details is not None:
            result["typed_details"] = self.typed_details
        return result


class ShadowDomainError(Exception):
    def __init__(self, error: ShadowError):
        super().__init__(error.message)
        self.error = error


class ConflictError(ShadowDomainError):
    def __init__(self, record_id: str, current_version: int):
        super().__init__(
            ShadowError(
                code="shadow.repository.expected-version-conflict",
                category="conflict",
                message=f"Expected version for {record_id} does not match the current version.",
                typed_details={"record_id": record_id, "current_version": current_version},
            )
        )


class RepositoryUnavailable(ShadowDomainError):
    def __init__(self) -> None:
        super().__init__(
            ShadowError(
                code="shadow.repository.unavailable",
                category="unavailable",
                message="Canonical Repository is unavailable.",
                retryable=True,
            )
        )
