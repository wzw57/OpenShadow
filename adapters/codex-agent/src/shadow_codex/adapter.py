from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.models import ExecutionRequest


@dataclass(frozen=True, slots=True)
class CodexExecutionResult:
    text: str
    usage: dict[str, int]
    execution_ref: str
    session_ref: str | None = None


@dataclass
class CodexAgentRuntimeAdapter:
    """Process-boundary adapter for the open-source Codex CLI."""

    executable: str = "codex"
    cwd: str | None = None
    model: str | None = None
    timeout_seconds: float = 300.0
    target_kind: str = "shadow.agent-runtime"
    extra_args: list[str] = field(default_factory=list)
    _events: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)

    @classmethod
    def from_environment(cls) -> CodexAgentRuntimeAdapter:
        timeout = os.getenv("SHADOW_CODEX_TIMEOUT_SECONDS", "300")
        try:
            timeout_seconds = float(timeout)
        except ValueError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.invalid-configuration",
                    category="validation",
                    message="SHADOW_CODEX_TIMEOUT_SECONDS must be a number.",
                )
            ) from exc
        extra_args = [item for item in os.getenv("SHADOW_CODEX_EXTRA_ARGS", "").split() if item]
        return cls(
            executable=os.getenv("SHADOW_CODEX_EXECUTABLE", "codex"),
            cwd=os.getenv("SHADOW_CODEX_CWD") or None,
            model=os.getenv("SHADOW_CODEX_MODEL") or None,
            timeout_seconds=timeout_seconds,
            extra_args=extra_args,
        )

    def describe(self) -> dict[str, Any]:
        body = {
            "descriptor_id": "shadow.adapter.codex",
            "descriptor_version": "1.0.0",
            "adapter_family": "shadow.execution",
            "implementation_ref": "openshadow://adapters/codex-agent",
            "implementation_version": "0.1.0",
            "supported_contracts": [
                {"contract_id": "shadow.execution", "version_range": "1.0.0"}
            ],
            "supported_target_kinds": [self.target_kind],
            "capabilities": [],
            "config_schema_ref": (
                "https://schemas.openshadow.dev/contracts/adapters/1.0.0#/$defs/AdapterDescriptor"
            ),
        }
        return body

    def configure_profile(self, profile: dict[str, Any]) -> None:
        """Apply non-secret deployment hints without importing Supervisor types."""
        workspace_dir = profile.get("workspace_dir")
        if isinstance(workspace_dir, str) and workspace_dir and self.cwd is None:
            self.cwd = workspace_dir

    def health(self) -> dict[str, Any]:
        executable = self._resolve_executable()
        return {"status": "healthy", "executable": executable}

    def execute(self, request: ExecutionRequest) -> CodexExecutionResult:
        typed_input = request.typed_input
        text = typed_input.get("text", "") if isinstance(typed_input, dict) else str(typed_input)
        if not text.strip():
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.empty-input",
                    category="validation",
                    message="Codex Runtime input must not be empty.",
                )
            )
        executable = self._resolve_executable()
        command = [executable, "exec", "--json", *self.extra_args]
        if self.model:
            command.extend(["--model", self.model])
        command.append(text)
        execution_ref = f"codex:{sha256_digest({'command': command[:-1], 'text': text})[7:31]}"
        try:
            completed = subprocess.run(
                command,
                cwd=self.cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.timeout",
                    category="unavailable",
                    message="Codex Runtime request timed out.",
                    typed_details={"execution_ref": execution_ref},
                )
            ) from exc
        except OSError as exc:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.unavailable",
                    category="unavailable",
                    message="Codex Runtime executable could not be started.",
                    typed_details={"execution_ref": execution_ref},
                )
            ) from exc

        events = self._parse_events(completed.stdout, execution_ref)
        self._events[execution_ref] = events
        if completed.returncode != 0:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.process-error",
                    category="unavailable",
                    message="Codex Runtime exited with a non-zero status.",
                    typed_details={
                        "execution_ref": execution_ref,
                        "returncode": completed.returncode,
                        "stderr_present": bool(completed.stderr.strip()),
                    },
                )
            )
        text_result = self._extract_text(events)
        if not text_result:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.protocol-incompatible",
                    category="incompatible",
                    message="Codex Runtime did not emit a final assistant message.",
                    typed_details={"execution_ref": execution_ref},
                )
            )
        return CodexExecutionResult(
            text=text_result,
            usage=self._extract_usage(events),
            execution_ref=execution_ref,
            session_ref=self._extract_session(events),
        )

    def events(self, execution_ref: str, after_cursor: str | None = None) -> list[dict[str, Any]]:
        events = self._events.get(execution_ref, [])
        if after_cursor is None:
            return events
        try:
            cursor = int(after_cursor)
        except ValueError:
            cursor = 0
        return [event for event in events if int(event["cursor"]) > cursor]

    def _resolve_executable(self) -> str:
        candidate = Path(self.executable)
        resolved = str(candidate) if candidate.is_file() else shutil.which(self.executable)
        if not resolved:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.executable-not-found",
                    category="unavailable",
                    message="Codex executable was not found.",
                    typed_details={"executable": self.executable},
                )
            )
        return resolved

    @staticmethod
    def _parse_events(stdout: str, execution_ref: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.runtime.protocol-incompatible",
                        category="incompatible",
                        message="Codex Runtime emitted a non-JSONL line.",
                        typed_details={"execution_ref": execution_ref},
                    )
                ) from exc
            if not isinstance(event, dict):
                continue
            events.append({"cursor": str(len(events) + 1), "execution_ref": execution_ref, **event})
        return events

    @staticmethod
    def _extract_text(events: list[dict[str, Any]]) -> str | None:
        result: str | None = None
        for event in events:
            item = event.get("item") if isinstance(event.get("item"), dict) else event
            event_type = item.get("type") or item.get("item_type")
            if event_type in {"agent_message", "assistant_message", "message"}:
                text = item.get("text") or item.get("content")
                if isinstance(text, list):
                    text = "".join(
                        part.get("text", "") for part in text if isinstance(part, dict)
                    )
                if isinstance(text, str) and text:
                    result = text
            if event.get("type") == "turn.completed" and isinstance(event.get("message"), str):
                result = event["message"]
        return result

    @staticmethod
    def _extract_usage(events: list[dict[str, Any]]) -> dict[str, int]:
        for event in reversed(events):
            usage = event.get("usage")
            if isinstance(usage, dict):
                return {
                    key: int(value)
                    for key, value in usage.items()
                    if key in {"input_tokens", "output_tokens", "total_tokens"}
                    and isinstance(value, (int, float))
                }
        return {}

    @staticmethod
    def _extract_session(events: list[dict[str, Any]]) -> str | None:
        for event in events:
            for key in ("thread_id", "session_id"):
                value = event.get(key)
                if isinstance(value, str) and value:
                    return value
        return None
