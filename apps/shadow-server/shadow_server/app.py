from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from shadow_application import (
    ActionService,
    AuthContext,
    ConversationService,
    DeterministicAuthVerifier,
    EnvironmentSecretResolver,
    IdentityService,
    MemoryService,
    OidcAuthVerifier,
    OutboxService,
    RuntimeSupervisor,
    SessionService,
    load_adapter,
    StateService,
    StaticSecretResolver,
    TaskService,
)
from shadow_kernel.admission import AdmissionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository
from shadow_kernel.runtime import RuntimeAdapter
from shadow_store import create_canonical_repository


class CreateConversationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=500)


class ContentBlockInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_type: str
    content_schema_ref: str
    typed_content: Any | None = None
    artifact_ref: dict[str, Any] | None = None


class ConversationTurnSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission_id: str
    message_type: str = "shadow.message.user"
    content_blocks: list[ContentBlockInput] = Field(min_length=1)
    turn_mode: str = "new"


class MemoryCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_kind: str
    content_schema_ref: str
    typed_content: Any
    applicability_scope: dict[str, Any]
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    source_dependency: str = "independent"


class StateProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: str = "shadow.state-proposal"
    proposed_operation: str
    target_ref: dict[str, Any] | None = None
    expected_version: int | None = Field(default=None, ge=1)
    state_key: str
    value_schema_ref: str
    proposed_value: Any = None
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    observed_at: str
    expires_at: str
    source_status: str = "available"
    proposal_reason: str | None = None


class TaskProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: str = "shadow.durable-task-proposal"
    proposed_operation: str
    target_ref: dict[str, Any] | None = None
    expected_version: int | None = Field(default=None, ge=1)
    task_key: str
    goal: str
    completion_criteria: Any
    waiting_condition: Any | None = None
    deadline: str | None = None
    result_ref: dict[str, Any] | None = None
    failure_summary: Any | None = None
    proposal_reason: str | None = None


class CheckpointCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checkpoint_kind: str
    checkpoint_digest: str
    runtime_target_kind: str
    runtime_capabilities: list[str] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    native_resume: bool = False


class CompletionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_ref: dict[str, Any] | None = None


class ActionProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: str = "shadow.action-proposal"
    proposed_operation: str = "create"
    action_kind: str
    target_ref: dict[str, Any]
    typed_parameters: dict[str, Any]
    data_classification: str
    side_effect_level: str
    required_capabilities: list[str] = Field(default_factory=list)
    deadline: str
    secret_refs: list[str] = Field(default_factory=list)
    provider_target_kind: str | None = None
    proposal_reason: str | None = None


class ActionApprovalProposalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: str = "shadow.action-approval-proposal"
    proposed_operation: str
    action_ref: dict[str, Any]
    expected_version: int = Field(ge=1)
    approver_ref: str
    decision: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    proposal_reason: str | None = None


class EndpointPairCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint_ref: str = Field(min_length=1, max_length=255)
    endpoint_kind: str = Field(default="shadow.endpoint.web", min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=200)
    capabilities: list[str] = Field(default_factory=list, max_length=100)


class SpaceCreateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    space_id: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=200)


class InvitationCreateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invitee_ref: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern="^(editor|viewer)$")
    expires_at: str


class InvitationAcceptCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invitation_token: str = Field(min_length=1, max_length=255)


class AuthSessionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential: str = Field(min_length=1, max_length=20_000)
    endpoint_ref: str | None = Field(default=None, max_length=255)
    ttl_seconds: int = Field(default=3600, ge=60, le=86_400)
    use_cookie: bool = True


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _principal(value: str | None) -> str:
    return value or "principal-local"


def _error_response(error: ShadowDomainError) -> JSONResponse:
    code = error.error.category
    status_code = {
        "validation": 422,
        "conflict": 409,
        "unavailable": 503,
        "unsupported": 409,
        "unauthorized": 403,
        "incompatible": 409,
    }.get(code, 500)
    if error.error.code in {
        "shadow.auth.unauthenticated",
        "shadow.auth.invalid-credential",
        "shadow.auth.session-expired",
        "shadow.auth.session-revoked",
    }:
        status_code = 401
    elif error.error.code in {"shadow.auth.context-mismatch", "shadow.auth.csrf-failed"}:
        status_code = 403
    return JSONResponse(
        status_code=status_code,
        content=error.error.as_dict(),
        media_type="application/problem+json",
    )


def _runtime_from_environment() -> RuntimeAdapter | None:
    factory_ref = os.getenv("SHADOW_RUNTIME_ADAPTER_FACTORY", "").strip()
    runtime_kind = os.getenv("SHADOW_RUNTIME_KIND", "deterministic").strip().lower()
    if not factory_ref and runtime_kind == "deterministic":
        return None
    if not factory_ref:
        raise ValueError(
            "SHADOW_RUNTIME_ADAPTER_FACTORY is required for a non-deterministic runtime"
        )
    try:
        return load_adapter(factory_ref)
    except ShadowDomainError as exc:
        raise ValueError(exc.error.message) from exc


def create_app(
    database_url: str | None = None, runtime_adapter: RuntimeAdapter | None = None
) -> FastAPI:
    root = _repo_root()
    registry = ContractRegistry(root)
    if database_url is None:
        configured_url = os.getenv("SHADOW_DATABASE_URL", "").strip()
        if configured_url:
            database_url = configured_url
        else:
            database_path = root / ".shadow" / "shadow.db"
            database_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{database_path.as_posix()}"
    repository = create_canonical_repository(database_url)
    authority = CommitAuthority(repository, registry)
    admission = AdmissionService(repository, authority)
    auth_mode = os.getenv("SHADOW_AUTH_MODE", "local-dev").strip().lower()
    if auth_mode not in {"local-dev", "oidc", "signed-session"}:
        raise ValueError("SHADOW_AUTH_MODE must be local-dev, oidc or signed-session")
    if auth_mode == "local-dev" and not os.getenv("SHADOW_AUTH_SESSION_SECRET"):
        secret_resolver = StaticSecretResolver(f"local-dev:{root.resolve()}")
        secret_ref = "memory:local-dev"
    else:
        secret_resolver = EnvironmentSecretResolver()
        secret_ref = "env:SHADOW_AUTH_SESSION_SECRET"
        if not os.getenv("SHADOW_AUTH_SESSION_SECRET"):
            raise ValueError("SHADOW_AUTH_SESSION_SECRET is required outside local-dev auth mode")
    if auth_mode == "oidc":
        required_oidc = {
            "SHADOW_OIDC_ISSUER": os.getenv("SHADOW_OIDC_ISSUER", "").strip(),
            "SHADOW_OIDC_AUDIENCE": os.getenv("SHADOW_OIDC_AUDIENCE", "").strip(),
            "SHADOW_OIDC_JWKS_URL": os.getenv("SHADOW_OIDC_JWKS_URL", "").strip(),
        }
        if any(not value for value in required_oidc.values()):
            raise ValueError("OIDC auth mode requires SHADOW_OIDC_ISSUER, SHADOW_OIDC_AUDIENCE and SHADOW_OIDC_JWKS_URL")
        auth_verifier = OidcAuthVerifier(
            issuer=os.getenv("SHADOW_OIDC_ISSUER", ""),
            audience=os.getenv("SHADOW_OIDC_AUDIENCE", ""),
            jwks_url=os.getenv("SHADOW_OIDC_JWKS_URL", ""),
            algorithms=[item.strip() for item in os.getenv("SHADOW_OIDC_ALGORITHMS", "RS256").split(",") if item.strip()],
        )
    else:
        auth_verifier = DeterministicAuthVerifier()
    sessions = SessionService(repository, authority, registry, secret_resolver, secret_ref=secret_ref)
    selected_runtime = runtime_adapter if runtime_adapter is not None else _runtime_from_environment()
    profile_path = Path(os.getenv("SHADOW_RUNTIME_PROFILE_PATH", str(root / "config" / "runtime-profiles.json")))
    supervisor = RuntimeSupervisor.from_file(profile_path) if profile_path.is_file() else RuntimeSupervisor.default()
    if selected_runtime is not None:
        supervisor.register_adapter("environment", selected_runtime, display_name="Environment Runtime")
    else:
        selected_runtime = supervisor.adapter_for()
    conversations = ConversationService(
        repository, authority, runtime_adapter=selected_runtime, admission=admission
    )
    memories = MemoryService(repository, authority, registry)
    states = StateService(repository, authority, registry)
    tasks = TaskService(repository, authority, registry)
    actions = ActionService(repository, authority, registry)
    identity = IdentityService(repository, authority, registry)
    outbox = OutboxService(repository, authority, registry)
    app = FastAPI(title="OpenShadow Phase 0-1", version="0.1.0")
    app.state.repository = repository
    app.state.conversations = conversations
    app.state.memories = memories
    app.state.states = states
    app.state.tasks = tasks
    app.state.admission = admission
    app.state.actions = actions
    app.state.identity = identity
    app.state.outbox = outbox
    app.state.auth_mode = auth_mode
    app.state.auth_verifier = auth_verifier
    app.state.sessions = sessions
    app.state.runtime_adapter = conversations.runtime_adapter
    app.state.runtime_supervisor = supervisor
    app.state.telemetry = {"requests_total": 0, "errors_total": 0, "request_duration_seconds_sum": 0.0}
    telemetry_logger = logging.getLogger("shadow.http")

    def _runtime_selection_guard() -> bool:
        try:
            runs = repository.query(record_types={"shadow.kernel.run"}, record_states={"active"}, limit=1_000)
        except Exception:
            return True
        return any(row.get("typed_payload", {}).get("lifecycle") in {"created", "queued", "running", "waiting", "paused", "cancelling"} for row in runs)

    supervisor.set_selection_guard(_runtime_selection_guard)

    @app.middleware("http")
    async def authenticate_request(request: Request, call_next: Any) -> JSONResponse | Any:
        path = request.url.path
        auth_exchange = path == "/v1/auth/session" and request.method == "POST"
        auth_config = path == "/v1/auth/config" and request.method == "GET"
        if path.startswith("/v1") and not auth_exchange and not auth_config:
            authorization = request.headers.get("Authorization", "")
            token = authorization.removeprefix("Bearer ").strip() if authorization else request.cookies.get("shadow_session")
            context: AuthContext | None = None
            if token:
                try:
                    context = sessions.verify_session(token)
                except ShadowDomainError as exc:
                    return _error_response(exc)
            elif auth_mode != "local-dev":
                return _error_response(ShadowDomainError(ShadowError(code="shadow.auth.unauthenticated", category="unauthorized", message="Authentication is required.")))
            if context is not None:
                request.state.auth_context = context
                # Production routes still declare the legacy header for API compatibility. Replace
                # any client-supplied value so it cannot override the verified principal.
                headers = [(key, value) for key, value in request.scope["headers"] if key.lower() != b"x-principal-ref"]
                headers.append((b"x-principal-ref", context.principal_ref.encode("utf-8")))
                request.scope["headers"] = headers
        return await call_next(request)

    @app.middleware("http")
    async def request_telemetry(request: Request, call_next: Any) -> JSONResponse | Any:
        correlation_id = request.headers.get("X-Correlation-Id") or f"correlation-{uuid.uuid4().hex}"
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        metrics = app.state.telemetry
        metrics["requests_total"] += 1
        metrics["request_duration_seconds_sum"] += elapsed
        if response.status_code >= 400:
            metrics["errors_total"] += 1
        response.headers["X-Correlation-Id"] = correlation_id
        telemetry_logger.info(
            "http_request",
            extra={"route": request.url.path, "method": request.method, "status": response.status_code, "correlation_id": correlation_id, "duration_ms": round(elapsed * 1000, 3)},
        )
        return response

    def _context(principal_ref: str, space_id: str, *, endpoint_ref: str | None = None, write: bool = False):
        return identity.require(principal_ref, space_id, endpoint_ref=endpoint_ref, write=write)

    def _owner_filter(context: Any) -> str | None:
        return context.principal_ref if identity._space(context.space_id) is None else None

    @app.exception_handler(ShadowDomainError)
    async def domain_error_handler(_request: Request, exc: ShadowDomainError) -> JSONResponse:
        return _error_response(exc)

    @app.get("/healthz")
    async def health() -> dict[str, Any]:
        return {
            "status": "healthy" if repository.available else "unavailable",
            "durable": repository.available,
        }

    @app.get("/readyz")
    async def readiness() -> JSONResponse:
        body = {
            "status": "healthy" if repository.available else "unavailable",
            "durable": repository.available,
        }
        return JSONResponse(status_code=200 if repository.available else 503, content=body)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        values = app.state.telemetry
        body = "\n".join(
            (
                "# TYPE shadow_http_requests_total counter",
                f"shadow_http_requests_total {values['requests_total']}",
                "# TYPE shadow_http_errors_total counter",
                f"shadow_http_errors_total {values['errors_total']}",
                "# TYPE shadow_http_request_duration_seconds_sum counter",
                f"shadow_http_request_duration_seconds_sum {values['request_duration_seconds_sum']}",
                "# TYPE shadow_store_ready gauge",
                f"shadow_store_ready {1 if repository.available else 0}",
            )
        ) + "\n"
        return Response(content=body, media_type="text/plain; version=0.0.4")

    @app.get("/v1/auth/config")
    async def auth_config() -> dict[str, Any]:
        return {
            "mode": auth_mode,
            "local_dev": auth_mode == "local-dev",
            "methods": ["deterministic"] if auth_mode == "local-dev" else ["oidc", "signed-session"],
            "session_cookie": "shadow_session",
        }

    @app.get("/v1/auth/session")
    async def auth_session(request: Request) -> dict[str, Any]:
        context = getattr(request.state, "auth_context", None)
        if context is None:
            raise ShadowDomainError(ShadowError(code="shadow.auth.unauthenticated", category="unauthorized", message="Authentication is required."))
        return {"context": context.as_dict()}

    @app.post("/v1/auth/session", status_code=status.HTTP_201_CREATED)
    async def create_auth_session(
        command: AuthSessionCommand,
        response: Response,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        if auth_mode == "signed-session":
            raise ShadowDomainError(ShadowError(code="shadow.auth.exchange-unsupported", category="unsupported", message="Signed-session mode verifies existing tokens and does not exchange credentials."))
        identity = auth_verifier.verify(command.credential)
        result = sessions.create_session(identity, idempotency_key=idempotency_key, ttl_seconds=command.ttl_seconds, endpoint_ref=command.endpoint_ref)
        # The token is returned only at exchange time; the canonical session stores its digest.
        if command.use_cookie:
            response.set_cookie("shadow_session", result["token"], httponly=True, secure=auth_mode != "local-dev", samesite="lax", max_age=command.ttl_seconds)
        return {
            "session": result["session"],
            "context": result["context"].as_dict(),
            "token": result["token"],
            "replayed": result["replayed"],
        }

    @app.post("/v1/auth/logout", status_code=status.HTTP_202_ACCEPTED)
    async def logout_auth_session(
        request: Request,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> JSONResponse:
        context = getattr(request.state, "auth_context", None)
        if context is None:
            raise ShadowDomainError(ShadowError(code="shadow.auth.unauthenticated", category="unauthorized", message="Authentication is required."))
        result = sessions.revoke(context, idempotency_key=idempotency_key)
        body = {"session": result["session"], "replayed": result["replayed"]}
        output = JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body)
        output.delete_cookie("shadow_session")
        return output

    @app.get("/v1/runtime")
    async def runtime_status() -> dict[str, Any]:
        """Expose the active non-secret Runtime descriptor for local clients."""
        active = supervisor.instances()
        active_instance = next(item for item in active if item["active"])
        return {
            "runtime": {
                "status": active_instance["state"]["health"] if active_instance["state"]["health"] != "unknown" else "configured",
                "target_kind": conversations.runtime_target_kind,
                "descriptor": active_instance["descriptor"] or conversations.runtime_descriptor.model_dump(mode="json", exclude_none=True),
                "health": active_instance["state"],
            }
        }

    @app.get("/v1/management/overview")
    async def management_overview() -> dict[str, Any]:
        return supervisor.overview(store_available=repository.available, web_ui_available=(root / "apps" / "shadow-web" / "dist").is_dir())

    @app.get("/v1/runtime/instances")
    async def runtime_instances() -> dict[str, Any]:
        return {"records": supervisor.instances()}

    @app.post("/v1/runtime/instances/{runtime_id}/start", status_code=status.HTTP_202_ACCEPTED)
    async def start_runtime(
        runtime_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return {"runtime": supervisor.start(runtime_id, idempotency_key)}

    @app.post("/v1/runtime/instances/{runtime_id}/stop", status_code=status.HTTP_202_ACCEPTED)
    async def stop_runtime(
        runtime_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return {"runtime": supervisor.stop(runtime_id, idempotency_key)}

    @app.post("/v1/runtime/instances/{runtime_id}/restart", status_code=status.HTTP_202_ACCEPTED)
    async def restart_runtime(
        runtime_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return {"runtime": supervisor.restart(runtime_id, idempotency_key)}

    @app.post("/v1/runtime/instances/{runtime_id}/select", status_code=status.HTTP_200_OK)
    async def select_runtime(
        runtime_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        selected = supervisor.select(runtime_id, idempotency_key)
        descriptor = conversations.install_runtime_adapter(supervisor.adapter_for(runtime_id))
        app.state.runtime_adapter = conversations.runtime_adapter
        selected["descriptor"] = descriptor.model_dump(mode="json", exclude_none=True)
        return {"runtime": selected}

    @app.get("/v1/runtime/instances/{runtime_id}/health")
    async def runtime_health(runtime_id: str) -> dict[str, Any]:
        return {"runtime": supervisor.health(runtime_id)}

    @app.post("/v1/runtime/instances/{runtime_id}/probe")
    async def runtime_probe(runtime_id: str) -> dict[str, Any]:
        return {"runtime": supervisor.probe(runtime_id)}

    @app.post("/v1/endpoints/pair", status_code=status.HTTP_201_CREATED)
    async def pair_endpoint(
        command: EndpointPairCommand,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return identity.pair_endpoint(
            principal_ref=x_principal_ref,
            space_id=x_space_id,
            endpoint_ref=command.endpoint_ref,
            endpoint_kind=command.endpoint_kind,
            label=command.label,
            capabilities=command.capabilities,
            idempotency_key=idempotency_key,
        )

    @app.get("/v1/endpoints")
    async def list_endpoints(
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        records = [
            row for row in identity._records("shadow.profile.endpoint")
            if row["typed_payload"].get("principal_ref") == x_principal_ref
        ]
        return {"records": records}

    @app.post("/v1/endpoints/{endpoint_id}/revoke", status_code=status.HTTP_202_ACCEPTED)
    async def revoke_endpoint(
        endpoint_id: str,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        return identity.revoke_endpoint(
            principal_ref=x_principal_ref,
            endpoint_ref=endpoint_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
        )

    @app.post("/v1/spaces", status_code=status.HTTP_201_CREATED)
    async def create_space(
        command: SpaceCreateCommand,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return identity.create_space(
            principal_ref=x_principal_ref,
            space_id=command.space_id,
            display_name=command.display_name,
            idempotency_key=idempotency_key,
        )

    @app.get("/v1/spaces")
    async def list_spaces(
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        return {"records": identity.list_spaces(x_principal_ref)}

    @app.get("/v1/spaces/{space_id}")
    async def get_space(
        space_id: str,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        identity.require(x_principal_ref, space_id)
        record = identity._space(space_id)
        if record is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.space.not-found",
                    category="validation",
                    message="Space was not found.",
                )
            )
        return {"record": record}

    @app.get("/v1/spaces/{space_id}/members")
    async def list_space_members(
        space_id: str,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        return {"records": identity.list_members(principal_ref=x_principal_ref, space_id=space_id)}

    @app.post("/v1/spaces/{space_id}/invitations", status_code=status.HTTP_202_ACCEPTED)
    async def create_invitation(
        space_id: str,
        command: InvitationCreateCommand,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return identity.invite(
            principal_ref=x_principal_ref,
            space_id=space_id,
            invitee_ref=command.invitee_ref,
            role=command.role,  # type: ignore[arg-type]
            expires_at=command.expires_at,
            idempotency_key=idempotency_key,
        )

    @app.post("/v1/invitations/{invitation_id}/accept", status_code=status.HTTP_202_ACCEPTED)
    async def accept_invitation(
        invitation_id: str,
        command: InvitationAcceptCommand,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        return identity.accept_invitation(
            principal_ref=x_principal_ref,
            invitation_id=invitation_id,
            invitation_token=command.invitation_token,
            idempotency_key=idempotency_key,
        )

    @app.delete("/v1/spaces/{space_id}/members/{principal_ref}", status_code=status.HTTP_202_ACCEPTED)
    async def revoke_space_member(
        space_id: str,
        principal_ref: str,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
    ) -> dict[str, Any]:
        return identity.revoke_member(
            principal_ref=x_principal_ref,
            space_id=space_id,
            target_principal=principal_ref,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
        )

    @app.post("/v1/conversations", status_code=status.HTTP_201_CREATED)
    async def create_conversation(
        command: CreateConversationCommand,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
        x_endpoint_ref: Annotated[str | None, Header(alias="X-Endpoint-Ref")] = None,
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        principal_ref = _principal(x_principal_ref)
        identity.require(principal_ref, x_space_id, endpoint_ref=x_endpoint_ref, write=True)
        return {
            "record": conversations.create_conversation(
                owner_ref=principal_ref,
                space_id=x_space_id,
                title=command.title,
                idempotency_key=idempotency_key or command.title or "default",
            )
        }

    @app.get("/v1/memories")
    async def list_memories(
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
    ) -> dict[str, Any]:
        context = _context(_principal(x_principal_ref), x_space_id)
        return {
            "records": memories.list_memories(
                owner_ref=_owner_filter(context), space_id=x_space_id
            )
        }

    @app.post("/v1/memories", status_code=status.HTTP_201_CREATED)
    async def create_memory(
        command: MemoryCommand,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        principal_ref = _principal(x_principal_ref)
        _context(principal_ref, x_space_id, write=True)
        key = idempotency_key or sha256_digest(command.model_dump(mode="json"))
        candidate = memories.propose_create(
            submitted_by=principal_ref,
            owner_ref=principal_ref,
            space_id=x_space_id,
            memory_kind=command.memory_kind,
            content_schema_ref=command.content_schema_ref,
            typed_content=command.typed_content,
            applicability_scope=command.applicability_scope,
            evidence_refs=command.evidence_refs,
            source_dependency=command.source_dependency,
        )
        return {"record": memories.commit_candidate(candidate, idempotency_key=key)}

    @app.get("/v1/memories/{memory_id}")
    async def get_memory(
        memory_id: str,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
    ) -> dict[str, Any]:
        record = memories.get_memory(memory_id)
        if record is None:
            raise HTTPException(404, detail="Memory not found")
        context = _context(_principal(x_principal_ref), x_space_id)
        if record["space_id"] != context.space_id:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.space.membership-denied",
                    category="unauthorized",
                    message="Memory is not in the requested Space.",
                )
            )
        return {"record": record}

    @app.delete("/v1/memories/{memory_id}", status_code=status.HTTP_202_ACCEPTED)
    async def delete_memory(
        memory_id: str,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header()],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        principal_ref = x_principal_ref
        _context(principal_ref, x_space_id, write=True)
        return {
            "record": memories.logical_delete(
                memory_id=memory_id,
                expected_version=expected_version,
                submitted_by=principal_ref,
                owner_ref=principal_ref,
                space_id=x_space_id,
                idempotency_key=idempotency_key,
            )
        }

    @app.post("/v1/memories/{memory_id}/corrections", status_code=status.HTTP_200_OK)
    async def correct_memory(
        memory_id: str,
        command: MemoryCommand,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header()],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        principal_ref = x_principal_ref
        _context(principal_ref, x_space_id, write=True)
        candidate = memories.propose_correction(
            submitted_by=principal_ref,
            owner_ref=principal_ref,
            space_id=x_space_id,
            memory_id=memory_id,
            expected_version=expected_version,
            memory_kind=command.memory_kind,
            content_schema_ref=command.content_schema_ref,
            typed_content=command.typed_content,
            applicability_scope=command.applicability_scope,
            evidence_refs=command.evidence_refs,
            source_dependency=command.source_dependency,
        )
        return {"record": memories.commit_correction(candidate, idempotency_key=idempotency_key)}

    @app.get("/v1/states")
    async def list_states(
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
        state_key: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        return {
            "records": states.list_states(
                owner_ref=_owner_filter(context), space_id=x_space_id, state_key=state_key, limit=limit
            )
        }

    @app.get("/v1/states/{state_id}")
    async def get_state(
        state_id: str,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        record = states.get_state(
            state_id, principal_ref=x_principal_ref, space_id=x_space_id, enforce_owner=identity._space(context.space_id) is None
        )
        if record is None:
            raise HTTPException(404, detail="State not found")
        return {"record": record}

    @app.post("/v1/proposals", status_code=status.HTTP_202_ACCEPTED)
    async def submit_proposal(
        command: StateProposalCommand | TaskProposalCommand | ActionProposalCommand | ActionApprovalProposalCommand,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    ) -> dict[str, Any]:
        _context(x_principal_ref, x_space_id, write=True)
        if isinstance(command, TaskProposalCommand):
            target_task_id = command.target_ref.get("record_id") if command.target_ref else None
            candidate = tasks.propose(
                submitted_by=x_principal_ref,
                owner_ref=x_principal_ref,
                space_id=x_space_id,
                operation=command.proposed_operation,
                task_key=command.task_key,
                goal=command.goal,
                completion_criteria=command.completion_criteria,
                target_task_id=target_task_id,
                expected_version=command.expected_version,
                waiting_condition=command.waiting_condition,
                deadline=command.deadline,
                result_ref=command.result_ref,
                failure_summary=command.failure_summary,
                proposal_reason=command.proposal_reason,
            )
            return {"record": tasks.submit_proposal(candidate, idempotency_key=idempotency_key)}
        if isinstance(command, ActionProposalCommand):
            candidate = actions.propose_action(
                submitted_by=x_principal_ref,
                owner_ref=x_principal_ref,
                space_id=x_space_id,
                action_kind=command.action_kind,
                target_ref=command.target_ref,
                typed_parameters=command.typed_parameters,
                data_classification=command.data_classification,
                side_effect_level=command.side_effect_level,
                required_capabilities=command.required_capabilities,
                deadline=command.deadline,
                secret_refs=command.secret_refs,
                provider_target_kind=command.provider_target_kind,
                proposal_reason=command.proposal_reason,
            )
            return {"record": actions.submit_proposal(candidate, idempotency_key=idempotency_key)}
        if isinstance(command, ActionApprovalProposalCommand):
            action_id = command.action_ref.get("record_id")
            if not action_id:
                raise HTTPException(422, detail="Action approval requires action_ref.record_id")
            candidate = actions.propose_approval(
                submitted_by=x_principal_ref,
                owner_ref=x_principal_ref,
                space_id=x_space_id,
                action_id=action_id,
                expected_version=command.expected_version,
                approver_ref=command.approver_ref,
                decision=command.decision,
                evidence_refs=command.evidence_refs,
                proposal_reason=command.proposal_reason,
            )
            return {"record": actions.submit_proposal(candidate, idempotency_key=idempotency_key)}
        if command.input_type != "shadow.state-proposal":
            raise HTTPException(422, detail="Unsupported Proposal type")
        target_state_id = None
        if command.target_ref is not None:
            target_state_id = command.target_ref.get("record_id")
        candidate = states.propose(
            submitted_by=x_principal_ref,
            owner_ref=x_principal_ref,
            space_id=x_space_id,
            operation=command.proposed_operation,
            state_key=command.state_key,
            value_schema_ref=command.value_schema_ref,
            proposed_value=command.proposed_value,
            evidence_refs=command.evidence_refs,
            source_refs=command.source_refs,
            observed_at=command.observed_at,
            expires_at=command.expires_at,
            source_status=command.source_status,
            target_state_id=target_state_id,
            expected_version=command.expected_version,
            proposal_reason=command.proposal_reason,
        )
        return {"record": states.submit_proposal(candidate, idempotency_key=idempotency_key)}

    @app.get("/v1/proposals/{proposal_id}")
    async def get_proposal(proposal_id: str) -> dict[str, Any]:
        record = repository.get(proposal_id)
        if record is None:
            raise HTTPException(404, detail="Proposal not found")
        return {"record": record}

    @app.post("/v1/proposals/{proposal_id}/accept")
    async def accept_proposal(
        proposal_id: str,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        proposal = repository.get(proposal_id)
        if proposal is None:
            raise HTTPException(404, detail="Proposal not found")
        _context(x_principal_ref, x_space_id, write=True)
        proposal_type = proposal.get("typed_payload", {}).get("proposal_type")
        if proposal_type == "shadow.durable-task-proposal":
            return tasks.accept_proposal(
                proposal_id=proposal_id,
                proposal_expected_version=expected_version,
                principal_ref=x_principal_ref,
                space_id=x_space_id,
                idempotency_key=idempotency_key,
            )
        if proposal_type in {"shadow.action-proposal", "shadow.action-approval-proposal"}:
            return actions.accept_proposal(
                proposal_id=proposal_id,
                proposal_expected_version=expected_version,
                principal_ref=x_principal_ref,
                space_id=x_space_id,
                idempotency_key=idempotency_key,
            )
        return states.accept_proposal(
            proposal_id=proposal_id,
            proposal_expected_version=expected_version,
            principal_ref=x_principal_ref,
            space_id=x_space_id,
            idempotency_key=idempotency_key,
        )

    @app.get("/v1/actions")
    async def list_actions(
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
        limit: int = 50,
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        return {"records": actions.list_actions(owner_ref=_owner_filter(context), space_id=x_space_id, limit=limit)}

    @app.get("/v1/actions/{action_id}")
    async def get_action(
        action_id: str,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        record = actions.get_action(action_id, x_principal_ref, x_space_id, enforce_owner=identity._space(context.space_id) is None)
        if record is None:
            raise HTTPException(404, detail="Action not found")
        return {"record": record}

    @app.get("/v1/tasks")
    async def list_tasks(
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
        limit: int = 50,
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        return {"records": tasks.list_tasks(owner_ref=_owner_filter(context), space_id=x_space_id, limit=limit)}

    @app.get("/v1/tasks/{task_id}")
    async def get_task(
        task_id: str,
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        context = _context(x_principal_ref, x_space_id)
        record = tasks.get_task(task_id, x_principal_ref, x_space_id, enforce_owner=identity._space(context.space_id) is None)
        if record is None:
            raise HTTPException(404, detail="Task not found")
        return {"record": record}

    @app.post("/v1/tasks/{task_id}/checkpoints")
    async def create_checkpoint(
        task_id: str,
        command: CheckpointCommand,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        _context(x_principal_ref, x_space_id, write=True)
        return tasks.create_checkpoint(
            task_id=task_id,
            expected_task_version=expected_version,
            principal_ref=x_principal_ref,
            space_id=x_space_id,
            checkpoint_kind=command.checkpoint_kind,
            checkpoint_digest=command.checkpoint_digest,
            runtime_target_kind=command.runtime_target_kind,
            runtime_capabilities=command.runtime_capabilities,
            artifact_refs=command.artifact_refs,
            native_resume=command.native_resume,
            idempotency_key=idempotency_key,
        )

    @app.post("/v1/tasks/{task_id}/completion")
    async def complete_task(
        task_id: str,
        command: CompletionCommand,
        expected_version: Annotated[int, Header(alias="Expected-Version", ge=1)],
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
        x_principal_ref: Annotated[str, Header(alias="X-Principal-Ref", min_length=1)],
        x_space_id: Annotated[str, Header(alias="X-Space-Id", min_length=1)],
    ) -> dict[str, Any]:
        _context(x_principal_ref, x_space_id, write=True)
        current = tasks.get_task(task_id, x_principal_ref, x_space_id)
        if current is None:
            raise HTTPException(404, detail="Task not found")
        candidate = tasks.propose(
            submitted_by=x_principal_ref,
            owner_ref=x_principal_ref,
            space_id=x_space_id,
            operation="complete",
            task_key=current["typed_payload"]["task_key"],
            goal=current["typed_payload"]["goal"],
            completion_criteria=current["typed_payload"]["completion_criteria"],
            target_task_id=task_id,
            expected_version=expected_version,
            result_ref=command.result_ref,
        )
        proposal = tasks.submit_proposal(candidate, idempotency_key=f"{idempotency_key}:proposal")
        return tasks.accept_proposal(
            proposal_id=proposal["record_id"],
            proposal_expected_version=proposal["version"],
            principal_ref=x_principal_ref,
            space_id=x_space_id,
            idempotency_key=idempotency_key,
        )

    @app.get("/v1/conversations")
    async def list_conversations(
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
    ) -> dict[str, Any]:
        context = _context(_principal(x_principal_ref), x_space_id)
        return {
            "records": conversations.list_conversations(_owner_filter(context), x_space_id)
        }

    @app.get("/v1/conversations/{conversation_id}")
    async def get_conversation(
        conversation_id: str,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
    ) -> dict[str, Any]:
        record = conversations.get_conversation(conversation_id)
        if record is None:
            raise HTTPException(404, detail="Conversation not found")
        _context(_principal(x_principal_ref), x_space_id)
        if record["space_id"] != x_space_id:
            raise HTTPException(404, detail="Conversation not found")
        return {"record": record}

    @app.get("/v1/conversations/{conversation_id}/messages")
    async def list_messages(
        conversation_id: str,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
    ) -> dict[str, Any]:
        conversation = conversations.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(404, detail="Conversation not found")
        _context(_principal(x_principal_ref), x_space_id)
        if conversation["space_id"] != x_space_id:
            raise HTTPException(404, detail="Conversation not found")
        return {"records": conversations.list_messages(conversation_id)}

    @app.post("/v1/conversations/{conversation_id}/turns", status_code=status.HTTP_202_ACCEPTED)
    async def submit_turn(
        conversation_id: str,
        submission: ConversationTurnSubmission,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_endpoint_ref: Annotated[str, Header()] = "endpoint-local-web",
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> JSONResponse:
        conversation = conversations.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(404, detail="Conversation not found")
        principal_ref = _principal(x_principal_ref)
        identity.require(
            principal_ref,
            conversation["space_id"],
            endpoint_ref=x_endpoint_ref,
            write=True,
        )
        block = submission.content_blocks[0]
        text = (
            block.typed_content.get("text")
            if isinstance(block.typed_content, dict)
            else block.typed_content
        )
        if not isinstance(text, str) or not text:
            raise HTTPException(422, detail="Phase 1 text adapter requires a text content block")
        result = conversations.submit_turn(
            conversation_id=conversation_id,
            principal_ref=principal_ref,
            endpoint_ref=x_endpoint_ref,
            text=text,
            idempotency_key=idempotency_key or submission.submission_id,
        )
        body = {
            "admission_ref": {
                "record_id": result.admission["record_id"],
                "version": result.admission["version"],
            },
            "message_ref": {
                "record_id": result.user_message["record_id"],
                "version": result.user_message["version"],
            },
            "request_ref": {
                "record_id": result.run["typed_payload"]["request_ref"]["record_id"],
                "version": 1,
            },
            "root_run_ref": {
                "record_id": result.run["record_id"],
                "version": result.run["version"],
            },
            "replayed": result.replayed,
            "durable": True,
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK if result.replayed else status.HTTP_202_ACCEPTED,
            content=body,
        )

    @app.get("/v1/admissions/{admission_id}")
    async def get_admission(admission_id: str) -> dict[str, Any]:
        return await _get_record(repository, admission_id)

    @app.get("/v1/requests/{request_id}")
    async def get_request(request_id: str) -> dict[str, Any]:
        return await _get_record(repository, request_id)

    @app.get("/v1/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        return await _get_record(repository, run_id)

    @app.post("/v1/runs/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
    async def retry_run(
        run_id: str,
        x_principal_ref: Annotated[str | None, Header()] = None,
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        result = conversations.retry_run(
            run_id=run_id,
            principal_ref=_principal(x_principal_ref),
            idempotency_key=idempotency_key or f"retry-{run_id}",
        )
        return {
            "admission_ref": {
                "record_id": result.admission["record_id"],
                "version": result.admission["version"],
            },
            "message_ref": {
                "record_id": result.assistant_message["record_id"],
                "version": result.assistant_message["version"],
            },
            "request_ref": {
                "record_id": result.run["typed_payload"]["request_ref"]["record_id"],
                "version": result.run["typed_payload"]["request_ref"]["version"],
            },
            "root_run_ref": {
                "record_id": result.run["record_id"],
                "version": result.run["version"],
            },
            "replayed": result.replayed,
            "durable": True,
        }

    @app.get("/v1/runs/{run_id}/events")
    async def stream_run_events(
        run_id: str, last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None
    ) -> StreamingResponse:
        if repository.get(run_id) is None:
            raise HTTPException(404, detail="Run not found")
        try:
            after = int(last_event_id or "0")
        except ValueError:
            after = 0
        events = repository.events(run_id, after)

        async def body() -> Any:
            for event in events:
                yield f"id: {event['sequence']}\nevent: {event['event_type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
        )

    @app.post("/v1/runs/{run_id}/cancel")
    async def cancel_run(run_id: str) -> JSONResponse:
        if repository.get(run_id) is None:
            raise HTTPException(404, detail="Run not found")
        return _error_response(
            ShadowDomainError(
                ShadowError(
                    code="shadow.execution.cancel-unsupported",
                    category="unsupported",
                    message="The deterministic adapter does not declare cancellation capability.",
                )
            )
        )

    web_dist = root / "apps" / "shadow-web" / "dist"
    if web_dist.is_dir():
        app.mount("/ui", StaticFiles(directory=web_dist, html=True), name="web-ui")

    return app


async def _get_record(repository: CanonicalRepository, record_id: str) -> dict[str, Any]:
    record = repository.get(record_id)
    if record is None:
        raise HTTPException(404, detail="Record not found")
    return {"record": record}


app = create_app()
