from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass, field
from http.client import HTTPException as HttpClientException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest


@dataclass(frozen=True, slots=True)
class HermesExecutionResult:
    """Normalized result returned by the external Hermes Agent Runtime."""

    text: str
    usage: dict[str, int]
    execution_ref: str
    session_ref: str | None = None


@dataclass
class HermesAgentRuntimeAdapter:
    """HTTP adapter for Hermes Agent's OpenAI-compatible API server.

    The adapter is intentionally synchronous because the existing Runtime Port is
    synchronous. It never writes Shadow records and it does not enable Hermes tools.
    """

    base_url: str = "http://127.0.0.1:8642/v1"
    model: str = "hermes-agent"
    api_key: str | None = None
    timeout_seconds: float = 60.0
    session_id: str | None = None
    target_kind: str = "shadow.agent-runtime"
    _events: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)

    @classmethod
    def from_environment(cls) -> HermesAgentRuntimeAdapter:
        timeout = os.getenv("SHADOW_HERMES_TIMEOUT_SECONDS", "60")
        try:
            timeout_seconds = float(timeout)
        except ValueError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.invalid-configuration",
                    category="validation",
                    message="SHADOW_HERMES_TIMEOUT_SECONDS must be a number.",
                )
            ) from exc
        return cls(
            base_url=os.getenv("SHADOW_HERMES_BASE_URL", "http://127.0.0.1:8642/v1"),
            model=os.getenv("SHADOW_HERMES_MODEL", "hermes-agent"),
            api_key=os.getenv("SHADOW_HERMES_API_KEY") or None,
            timeout_seconds=timeout_seconds,
            session_id=os.getenv("SHADOW_HERMES_SESSION_ID") or None,
        )

    def describe(self) -> dict[str, Any]:
        body = {
            "descriptor_id": "shadow.adapter.hermes",
            "descriptor_version": "1.0.0",
            "adapter_family": "shadow.execution",
            "implementation_ref": "openshadow://adapters/hermes-agent",
            "implementation_version": "0.1.0",
            "supported_contracts": [
                {"contract_id": "shadow.execution", "version_range": "1.0.0"}
            ],
            "supported_target_kinds": [self.target_kind],
            # Tool/capability declarations are deliberately empty in this slice.
            "capabilities": [],
            "config_schema_ref": (
                "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor"
            ),
        }
        return body

    def configure_profile(self, profile: dict[str, Any]) -> None:
        """Apply a profile's non-secret health endpoint to the adapter."""
        health_url = profile.get("health_url")
        if isinstance(health_url, str) and health_url:
            self.base_url = health_url.rstrip("/")

    def execute(self, text: str) -> HermesExecutionResult:
        if not text:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.empty-input",
                    category="validation",
                    message="Hermes Runtime input must not be empty.",
                )
            )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": text}],
            "stream": False,
        }
        headers = self._headers()
        if self.session_id:
            headers["X-Hermes-Session-Id"] = self.session_id
        response = self._request_json("POST", "/chat/completions", payload, headers)
        try:
            choice = response["choices"][0]
            message = choice["message"]
            result_text = message.get("content") or ""
            execution_ref = str(response.get("id") or self._execution_ref(text))
            usage = self._usage(response.get("usage"))
        except (KeyError, IndexError, TypeError) as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.protocol-incompatible",
                    category="incompatible",
                    message="Hermes response did not match the Chat Completions contract.",
                    typed_details={"response_keys": sorted(response)},
                )
            ) from exc
        self._events[execution_ref] = [
            {"cursor": "1", "event_type": "runtime.completed", "execution_ref": execution_ref}
        ]
        return HermesExecutionResult(
            text=result_text,
            usage=usage,
            execution_ref=execution_ref,
            session_ref=self.session_id,
        )

    def events(self, execution_ref: str, after_cursor: str | None = None) -> list[dict[str, Any]]:
        events = self._events.get(execution_ref, [])
        try:
            cursor = int(after_cursor or "0")
        except ValueError:
            cursor = 0
        return [event for event in events if int(event["cursor"]) > cursor]

    def health(self) -> dict[str, Any]:
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        response = self._request_json("GET", f"{base}/health", None, self._headers())
        return response

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.base_url.rstrip('/')}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                raw = response.read()
        except HTTPError as exc:
            category = "unauthorized" if exc.code in {401, 403} else "unavailable"
            retryable = exc.code >= 500 or exc.code in {408, 429}
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.http-error",
                    category=category,
                    message=f"Hermes Runtime returned HTTP {exc.code}.",
                    retryable=retryable,
                    typed_details={"status_code": exc.code, "url": url},
                )
            ) from exc
        except (URLError, TimeoutError, HttpClientException) as exc:
            reason = getattr(exc, "reason", str(exc))
            is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or "timed out" in str(reason).lower()
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.timeout" if is_timeout else "shadow.runtime.unavailable",
                    category="timeout" if is_timeout else "unavailable",
                    message="Hermes Runtime request timed out." if is_timeout else "Hermes Runtime is unavailable.",
                    retryable=True,
                    typed_details={"url": url, "reason": str(reason)},
                )
            ) from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.protocol-incompatible",
                    category="incompatible",
                    message="Hermes Runtime returned a non-JSON response.",
                    typed_details={"url": url},
                )
            ) from exc
        if not isinstance(decoded, dict):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.protocol-incompatible",
                    category="incompatible",
                    message="Hermes Runtime response must be a JSON object.",
                    typed_details={"url": url},
                )
            )
        return decoded

    @staticmethod
    def _usage(usage: Any) -> dict[str, int]:
        if not isinstance(usage, dict):
            return {}
        return {
            str(key): int(value)
            for key, value in usage.items()
            if isinstance(value, (int, float))
        }

    @staticmethod
    def _execution_ref(text: str) -> str:
        return f"hermes:{sha256_digest({'text': text})[7:31]}"
