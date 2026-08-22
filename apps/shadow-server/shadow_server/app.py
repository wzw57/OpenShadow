from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from shadow_application import ConversationService, MemoryService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository
from shadow_store import SqliteCanonicalRepository


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
    return JSONResponse(
        status_code=status_code,
        content=error.error.as_dict(),
        media_type="application/problem+json",
    )


def create_app(database_url: str | None = None) -> FastAPI:
    root = _repo_root()
    registry = ContractRegistry(root)
    if database_url is None:
        database_path = root / ".shadow" / "shadow.db"
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{database_path.as_posix()}"
    repository = SqliteCanonicalRepository(database_url)
    authority = CommitAuthority(repository, registry)
    conversations = ConversationService(repository, authority)
    memories = MemoryService(repository, authority, registry)
    app = FastAPI(title="OpenShadow Phase 0-1", version="0.1.0")
    app.state.repository = repository
    app.state.conversations = conversations
    app.state.memories = memories

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

    @app.post("/v1/conversations", status_code=status.HTTP_201_CREATED)
    async def create_conversation(
        command: CreateConversationCommand,
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str, Header()] = "space-personal",
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        return {
            "record": conversations.create_conversation(
                owner_ref=_principal(x_principal_ref),
                space_id=x_space_id,
                title=command.title,
                idempotency_key=idempotency_key or command.title or "default",
            )
        }

    @app.get("/v1/memories")
    async def list_memories(
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        return {
            "records": memories.list_memories(
                owner_ref=_principal(x_principal_ref), space_id=x_space_id
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
    async def get_memory(memory_id: str) -> dict[str, Any]:
        record = memories.get_memory(memory_id)
        if record is None:
            raise HTTPException(404, detail="Memory not found")
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

    @app.get("/v1/conversations")
    async def list_conversations(
        x_principal_ref: Annotated[str | None, Header()] = None,
        x_space_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        return {
            "records": conversations.list_conversations(_principal(x_principal_ref), x_space_id)
        }

    @app.get("/v1/conversations/{conversation_id}")
    async def get_conversation(conversation_id: str) -> dict[str, Any]:
        record = conversations.get_conversation(conversation_id)
        if record is None:
            raise HTTPException(404, detail="Conversation not found")
        return {"record": record}

    @app.get("/v1/conversations/{conversation_id}/messages")
    async def list_messages(conversation_id: str) -> dict[str, Any]:
        if conversations.get_conversation(conversation_id) is None:
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
            principal_ref=_principal(x_principal_ref),
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

    return app


async def _get_record(repository: CanonicalRepository, record_id: str) -> dict[str, Any]:
    record = repository.get(record_id)
    if record is None:
        raise HTTPException(404, detail="Record not found")
    return {"record": record}


app = create_app()
