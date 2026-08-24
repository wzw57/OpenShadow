from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any

from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.runtime import RuntimeAdapter


def _error(code: str, message: str, *, category: str = "validation", details: dict[str, Any] | None = None) -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))


def load_factory(reference: str) -> Callable[[], RuntimeAdapter]:
    if ":" not in reference:
        raise _error("shadow.runtime.invalid-profile", "adapter_factory must use '<module>:<factory>'.")
    module_name, factory_name = reference.split(":", 1)
    if not module_name or not factory_name or any(part.startswith("_") for part in factory_name.split(".")):
        raise _error("shadow.runtime.invalid-profile", "adapter_factory is not a valid public factory reference.")
    try:
        factory: Any = importlib.import_module(module_name)
        for attribute in factory_name.split("."):
            factory = getattr(factory, attribute)
    except (ImportError, AttributeError) as exc:
        raise _error(
            "shadow.runtime.adapter-unavailable",
            "The configured Runtime Adapter factory could not be loaded.",
            category="unavailable",
            details={"adapter_factory": reference},
        ) from exc
    if not callable(factory):
        raise _error("shadow.runtime.invalid-profile", "adapter_factory is not callable.")
    return factory


def load_adapter(reference: str) -> RuntimeAdapter:
    """Instantiate and validate a configured RuntimeAdapter through one loader."""
    adapter = load_factory(reference)()
    required_methods = ("describe", "execute", "events")
    if not all(callable(getattr(adapter, method, None)) for method in required_methods):
        raise _error(
            "shadow.runtime.invalid-adapter",
            "Runtime Adapter does not implement the required Port.",
            category="incompatible",
            details={"adapter_factory": reference},
        )
    return adapter


@dataclass(frozen=True, slots=True)
class RuntimeProfile:
    runtime_id: str
    display_name: str
    adapter_factory: str
    target_kind: str
    enabled: bool = False
    auto_start: bool = False
    launch_command: tuple[str, ...] = ()
    launch_cwd: str | None = None
    health_url: str | None = None
    workspace_dir: str | None = None

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> RuntimeProfile:
        runtime_id = str(body.get("runtime_id", ""))
        if not runtime_id or any(char in runtime_id for char in "/\\"):
            raise _error("shadow.runtime.invalid-profile", "runtime_id must be a stable path-free identifier.")
        launch = body.get("launch") or {}
        command = launch.get("command") or []
        if not isinstance(command, list) or any(not isinstance(item, str) or not item for item in command):
            raise _error("shadow.runtime.invalid-profile", "launch.command must be a non-empty string array.")
        for forbidden in ("shell", "script", "secret", "token"):
            if forbidden in launch:
                raise _error("shadow.runtime.invalid-profile", "launch cannot contain shell or secret fields.")
        return cls(
            runtime_id=runtime_id,
            display_name=str(body.get("display_name") or runtime_id),
            adapter_factory=str(body.get("adapter_factory", "")),
            target_kind=str(body.get("target_kind", "shadow.agent-runtime")),
            enabled=bool(body.get("enabled", False)),
            auto_start=bool(body.get("auto_start", False)),
            launch_command=tuple(command),
            launch_cwd=launch.get("cwd"),
            health_url=body.get("health", {}).get("url") if isinstance(body.get("health"), dict) else None,
            workspace_dir=body.get("workspace_dir"),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "display_name": self.display_name,
            "adapter_factory": self.adapter_factory,
            "target_kind": self.target_kind,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "launch": {"configured": bool(self.launch_command), "cwd_configured": bool(self.launch_cwd)},
            "health": {"url_configured": bool(self.health_url)},
            "workspace_configured": bool(self.workspace_dir),
        }


@dataclass
class RuntimeState:
    lifecycle: str = "stopped"
    health: str = "unknown"
    pid: int | None = None
    external_ref: str | None = None
    last_error: dict[str, Any] | None = None
    updated_at: str = field(default_factory=utc_timestamp)

    def public_dict(self) -> dict[str, Any]:
        return {
            "lifecycle": self.lifecycle,
            "health": self.health,
            "pid": self.pid,
            "external_ref": self.external_ref,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
        }


class RuntimeSupervisor:
    """Local process and Runtime Adapter control plane."""

    def __init__(
        self,
        profiles: list[RuntimeProfile],
        *,
        active_runtime_id: str,
        selection_guard: Callable[[], bool] | None = None,
    ) -> None:
        if not profiles:
            raise _error("shadow.runtime.invalid-profile", "At least one Runtime profile is required.")
        self._profiles = {profile.runtime_id: profile for profile in profiles}
        if active_runtime_id not in self._profiles:
            raise _error("shadow.runtime.not-found", "The configured active Runtime does not exist.")
        self._active_runtime_id = active_runtime_id
        self._states = {runtime_id: RuntimeState() for runtime_id in self._profiles}
        self._adapters: dict[str, RuntimeAdapter] = {}
        self._processes: dict[str, subprocess.Popen[Any]] = {}
        self._idempotency: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
        self._selection_guard = selection_guard
        self._lock = RLock()

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        selection_guard: Callable[[], bool] | None = None,
    ) -> RuntimeSupervisor:
        if not path.is_file():
            raise _error("shadow.runtime.profile-not-found", "Runtime profile file was not found.", details={"path": str(path)})
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise _error("shadow.runtime.invalid-profile", "Runtime profile file is not valid JSON.") from exc
        if not isinstance(body, dict) or not isinstance(body.get("profiles"), list):
            raise _error("shadow.runtime.invalid-profile", "Runtime profile file must contain a profiles array.")
        profiles = [RuntimeProfile.from_dict(item) for item in body["profiles"]]
        return cls(profiles, active_runtime_id=str(body.get("active_runtime_id", profiles[0].runtime_id)), selection_guard=selection_guard)

    @classmethod
    def default(cls, *, selection_guard: Callable[[], bool] | None = None) -> RuntimeSupervisor:
        return cls(
            [
                RuntimeProfile(
                    runtime_id="deterministic",
                    display_name="Deterministic Runtime",
                    adapter_factory="shadow_adapters:create_runtime_adapter",
                    target_kind="shadow.deterministic-runner",
                    enabled=True,
                )
            ],
            active_runtime_id="deterministic",
            selection_guard=selection_guard,
        )

    @property
    def active_runtime_id(self) -> str:
        return self._active_runtime_id

    def set_selection_guard(self, guard: Callable[[], bool] | None) -> None:
        self._selection_guard = guard

    def register_adapter(self, runtime_id: str, adapter: RuntimeAdapter, *, display_name: str | None = None) -> None:
        with self._lock:
            if runtime_id not in self._profiles:
                descriptor = adapter.describe()
                self._profiles[runtime_id] = RuntimeProfile(
                    runtime_id=runtime_id,
                    display_name=display_name or runtime_id,
                    adapter_factory="runtime:injected",
                    target_kind=descriptor["supported_target_kinds"][0],
                    enabled=True,
                )
                self._states[runtime_id] = RuntimeState()
            self._adapters[runtime_id] = adapter
            self._active_runtime_id = runtime_id

    def adapter_for(self, runtime_id: str | None = None) -> RuntimeAdapter:
        runtime_id = runtime_id or self._active_runtime_id
        profile = self._profile(runtime_id)
        with self._lock:
            adapter = self._adapters.get(runtime_id)
            if adapter is None:
                if not profile.enabled:
                    raise _error("shadow.runtime.disabled", "The Runtime profile is disabled.", details={"runtime_id": runtime_id})
                adapter = load_adapter(profile.adapter_factory)
                configure = getattr(adapter, "configure_profile", None)
                if callable(configure):
                    configure({"workspace_dir": profile.workspace_dir, "health_url": profile.health_url})
                self._validate_adapter(adapter, profile)
                self._adapters[runtime_id] = adapter
            return adapter

    def start(self, runtime_id: str, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            profile = self._profile(runtime_id)
            if not profile.enabled:
                raise _error("shadow.runtime.disabled", "The Runtime profile is disabled.", details={"runtime_id": runtime_id})
            digest = sha256_digest({"runtime_id": runtime_id, "operation": "start"})
            replay = self._replay("start", idempotency_key, digest)
            if replay is not None:
                return replay
            state = self._states[runtime_id]
            process = self._processes.get(runtime_id)
            if process is not None and process.poll() is None:
                result = self._snapshot(runtime_id, replayed=True)
                self._remember("start", idempotency_key, digest, result)
                return result
            state.lifecycle = "starting"
            state.health = "unknown"
            state.last_error = None
            state.updated_at = utc_timestamp()
            try:
                if profile.launch_command:
                    self._validate_launch(profile)
                    process = subprocess.Popen(
                        list(profile.launch_command),
                        cwd=profile.launch_cwd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=False,
                        env=dict(os.environ),
                    )
                    self._processes[runtime_id] = process
                    state.pid = process.pid
                adapter = self.adapter_for(runtime_id)
                health_fn = getattr(adapter, "health", None)
                if callable(health_fn):
                    self._wait_for_health(health_fn, runtime_id)
                if process is not None and process.poll() is not None:
                    raise _error(
                        "shadow.runtime.process-start-failed",
                        "Runtime process exited during startup.",
                        category="unavailable",
                        details={"returncode": process.returncode},
                    )
                state.lifecycle = "healthy"
                state.health = "healthy"
            except ShadowDomainError as exc:
                state.lifecycle = "failed"
                state.health = "unavailable"
                state.last_error = exc.error.as_dict()
                state.updated_at = utc_timestamp()
                self._terminate(runtime_id)
                raise
            state.updated_at = utc_timestamp()
            result = self._snapshot(runtime_id, replayed=False)
            self._remember("start", idempotency_key, digest, result)
            return result

    def stop(self, runtime_id: str, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            self._profile(runtime_id)
            digest = sha256_digest({"runtime_id": runtime_id, "operation": "stop"})
            replay = self._replay("stop", idempotency_key, digest)
            if replay is not None:
                return replay
            state = self._states[runtime_id]
            state.lifecycle = "stopping"
            self._terminate(runtime_id)
            state.lifecycle = "stopped"
            state.health = "unknown"
            state.pid = None
            state.updated_at = utc_timestamp()
            result = self._snapshot(runtime_id, replayed=False)
            self._remember("stop", idempotency_key, digest, result)
            return result

    def restart(self, runtime_id: str, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            self._profile(runtime_id)
            digest = sha256_digest({"runtime_id": runtime_id, "operation": "restart"})
            replay = self._replay("restart", idempotency_key, digest)
            if replay is not None:
                return replay
            self.stop(runtime_id, f"{idempotency_key}:stop")
            result = self.start(runtime_id, f"{idempotency_key}:start")
            result["replayed"] = False
            self._remember("restart", idempotency_key, digest, result)
            return result

    def select(self, runtime_id: str, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            profile = self._profile(runtime_id)
            if not profile.enabled:
                raise _error("shadow.runtime.disabled", "The Runtime profile is disabled.", details={"runtime_id": runtime_id})
            digest = sha256_digest({"runtime_id": runtime_id, "operation": "select"})
            replay = self._replay("select", idempotency_key, digest)
            if replay is not None:
                return replay
            if self._selection_guard and self._selection_guard():
                raise _error("shadow.runtime.selection-conflict", "Runtime selection is blocked by an executing Run.", category="conflict")
            state = self._states[runtime_id]
            if state.lifecycle != "healthy":
                raise _error("shadow.runtime.health-unavailable", "Only a healthy Runtime can become active.", category="unavailable")
            self._active_runtime_id = runtime_id
            result = self._snapshot(runtime_id, replayed=False)
            self._remember("select", idempotency_key, digest, result)
            return result

    def health(self, runtime_id: str) -> dict[str, Any]:
        with self._lock:
            self._profile(runtime_id)
            adapter = self.adapter_for(runtime_id)
            health_fn = getattr(adapter, "health", None)
            if not callable(health_fn):
                return self._snapshot(runtime_id, replayed=False)
            try:
                health = health_fn()
            except ShadowDomainError as exc:
                state = self._states[runtime_id]
                state.health = "unavailable"
                state.last_error = exc.error.as_dict()
                state.updated_at = utc_timestamp()
                raise
            state = self._states[runtime_id]
            state.health = "healthy"
            if state.lifecycle in {"stopped", "unknown"}:
                state.lifecycle = "healthy"
            state.last_error = None
            state.updated_at = utc_timestamp()
            return {**self._snapshot(runtime_id, replayed=False), "health_detail": health}

    def probe(self, runtime_id: str) -> dict[str, Any]:
        return self.health(runtime_id)

    def instances(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._snapshot(runtime_id, replayed=False) for runtime_id in self._profiles]

    def overview(self, *, store_available: bool, web_ui_available: bool) -> dict[str, Any]:
        return {
            "api": {"status": "healthy"},
            "store": {"status": "healthy" if store_available else "unavailable", "durable": store_available},
            "web_ui": {"status": "configured" if web_ui_available else "unavailable"},
            "active_runtime_id": self._active_runtime_id,
            "runtimes": self.instances(),
            "generated_at": utc_timestamp(),
        }

    def _profile(self, runtime_id: str) -> RuntimeProfile:
        profile = self._profiles.get(runtime_id)
        if profile is None:
            raise _error("shadow.runtime.not-found", "Runtime profile was not found.", details={"runtime_id": runtime_id})
        return profile

    def _snapshot(self, runtime_id: str, *, replayed: bool) -> dict[str, Any]:
        profile = self._profile(runtime_id)
        adapter = self._adapters.get(runtime_id)
        descriptor: dict[str, Any] | None = None
        if adapter is not None:
            try:
                descriptor = adapter.describe()
            except Exception:
                descriptor = None
        return {
            "runtime_id": runtime_id,
            "active": runtime_id == self._active_runtime_id,
            "profile": profile.public_dict(),
            "descriptor": descriptor,
            "state": self._states[runtime_id].public_dict(),
            "replayed": replayed,
        }

    def _validate_adapter(self, adapter: RuntimeAdapter, profile: RuntimeProfile) -> None:
        descriptor = adapter.describe()
        target_kinds = descriptor.get("supported_target_kinds", [])
        if profile.target_kind not in target_kinds:
            raise _error("shadow.runtime.target-kind-mismatch", "Runtime Adapter does not support the profile target kind.", category="incompatible")

    def _validate_launch(self, profile: RuntimeProfile) -> None:
        command = profile.launch_command
        executable = shutil.which(command[0]) or (command[0] if Path(command[0]).is_file() else None)
        if executable is None:
            raise _error("shadow.runtime.executable-not-found", "Runtime launch executable was not found.", category="unavailable")
        if profile.launch_cwd and not Path(profile.launch_cwd).is_dir():
            raise _error("shadow.runtime.invalid-profile", "Runtime launch cwd does not exist.")

    def _wait_for_health(self, health_fn: Callable[[], Any], runtime_id: str) -> None:
        last_error: ShadowDomainError | None = None
        for _ in range(30):
            try:
                health_fn()
                return
            except ShadowDomainError as exc:
                last_error = exc
                process = self._processes.get(runtime_id)
                if process is not None and process.poll() is not None:
                    break
                time.sleep(0.1)
        raise _error(
            "shadow.runtime.health-unavailable",
            "Runtime did not become healthy after startup.",
            category="unavailable",
            details=last_error.error.as_dict() if last_error else None,
        )

    def _terminate(self, runtime_id: str) -> None:
        process = self._processes.pop(runtime_id, None)
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _replay(self, operation: str, key: str, digest: str) -> dict[str, Any] | None:
        prior = self._idempotency.get((operation, key))
        if prior is None:
            return None
        prior_digest, result = prior
        if prior_digest != digest:
            raise _error("shadow.repository.idempotency-mismatch", "Runtime idempotency key was reused with different content.", category="conflict")
        replay = dict(result)
        replay["replayed"] = True
        return replay

    def _remember(self, operation: str, key: str, digest: str, result: dict[str, Any]) -> None:
        self._idempotency[(operation, key)] = (digest, dict(result))


__all__ = ["RuntimeProfile", "RuntimeState", "RuntimeSupervisor", "load_adapter", "load_factory"]
