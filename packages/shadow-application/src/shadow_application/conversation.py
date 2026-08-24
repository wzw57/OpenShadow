from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shadow_kernel.adapters import AdapterDescriptor, AdapterRegistry
from shadow_kernel.admission import AdmissionService
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    CommitOperation,
    CommitPlan,
    ContentBlock,
    ConversationPayload,
    ExecutionAttemptPayload,
    MessagePayload,
    Provenance,
    RecordVersionRef,
    RequestPayload,
    RunPayload,
    StableRecordRef,
)
from shadow_kernel.repository import CanonicalRepository
from shadow_kernel.runtime import RuntimeAdapter

PROFILE_SCHEMA = "https://schemas.openshadow.dev/contracts/profiles/1.0.0"
KERNEL_SCHEMA = "https://schemas.openshadow.dev/contracts/kernel/1.0.0"
ADAPTER_SCHEMA = "https://schemas.openshadow.dev/contracts/adapters/1.0.0"
RETENTION_REF = StableRecordRef(record_id="retention-default")


@dataclass(frozen=True, slots=True)
class TurnResult:
    conversation: dict[str, Any]
    run: dict[str, Any]
    user_message: dict[str, Any]
    assistant_message: dict[str, Any]
    admission: dict[str, Any]
    ephemeral: bool = False
    replayed: bool = False


class ConversationService:
    """Phase 1 application flow: conversation -> admission -> run -> result."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        runtime_adapter: RuntimeAdapter | None = None,
        admission: AdmissionService | None = None,
    ):
        if runtime_adapter is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.adapter-not-injected",
                    category="incompatible",
                    message="ConversationService requires a RuntimeAdapter supplied by the composition root.",
                )
            )
        self.repository = repository
        self.authority = authority
        self.admission = admission or AdmissionService(repository, authority)
        self.adapters = AdapterRegistry()
        self.runtime_adapter = runtime_adapter
        self.runtime_descriptor = self._ensure_runtime_descriptor()
        self.runtime_target_kind = self.runtime_descriptor.supported_target_kinds[0]

    def create_conversation(
        self,
        *,
        owner_ref: str,
        space_id: str,
        title: str | None = None,
        idempotency_key: str = "default",
    ) -> dict[str, Any]:
        record_id = f"conversation-{sha256_digest({'owner': owner_ref, 'space': space_id, 'key': idempotency_key})[7:31]}"
        payload = ConversationPayload(
            title=title,
            conversation_state="open",
            message_refs=[],
            queued_run_refs=[],
        )
        provenance = Provenance(
            origin_type="shadow.origin.user-command", origin_ref=f"create-conversation-{record_id}"
        )
        operation = self._operation(
            operation_id=f"operation-{record_id}",
            operation="create",
            record_id=record_id,
            record_type="shadow.profile.conversation",
            target_schema_ref=f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=owner_ref,
            typed_payload=payload.model_dump(mode="json", exclude_none=True),
            provenance=provenance,
        )
        if admitted.replayed:
            return TurnResult(
                conversation=self.repository.get(conversation_id) or {},
                run=self.repository.get(ids["run"]) or {},
                user_message=self.repository.get(ids["message-user"]) or {},
                assistant_message=self.repository.get(ids["message-assistant"]) or {},
                admission=self.repository.get(ids["admission"]) or {},
                ephemeral=False,
                replayed=True,
            )
        self.repository.append_event(ids["run"], "shadow.run.started", {"run_id": ids["run"], "attempt_id": ids["attempt"]})
        try:
            output = self.runtime_adapter.execute(text)
            output_text = getattr(output, "text", None)
            if not isinstance(output_text, str):
                raise TypeError("Runtime Adapter result did not contain text.")
            runtime_failure: dict[str, Any] | None = None
        except Exception as exc:  # Provider failures are durable unknown outcomes, never successful turns.
            output = None
            output_text = None
            runtime_failure = {"code": "shadow.runtime.outcome-unknown", "reason": str(exc)[:500]}

        initial_run = self.repository.get(ids["run"])
        initial_attempt = self.repository.get(ids["attempt"])
        initial_conversation = self.repository.get(conversation_id)
        if initial_run is None or initial_attempt is None or initial_conversation is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.dispatch-boundary-missing",
                    category="internal",
                    message="Durable dispatch records could not be recovered after the initial commit.",
                )
            )
        final_provenance = Provenance(origin_type="shadow.origin.runtime-result", origin_ref=f"result-{token}")
        if runtime_failure is not None:
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(
                update={"lifecycle": "waiting", "failure_summary": runtime_failure, "terminal_at": None}
            )
            final_attempt = ExecutionAttemptPayload.model_validate(initial_attempt["typed_payload"]).model_copy(
                update={"lifecycle": "outcome_unknown", "failure_summary": runtime_failure, "finished_at": None}
            )
            final_operations = [
                self._operation(
                    f"operation-result-attempt-{token}", "update", ids["attempt"], "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload", owner_ref, space_id, principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True), final_provenance, expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-result-run-{token}", "update", ids["run"], "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload", owner_ref, space_id, principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True), final_provenance, expected_version=initial_run["version"],
                ),
            ]
        else:
            assistant_message = MessagePayload(
                conversation_ref=StableRecordRef(record_id=conversation_id),
                sequence=len(current_payload.message_refs) + 2,
                message_type="shadow.message.assistant",
                author_ref=self.runtime_descriptor.descriptor_id,
                content_blocks=[ContentBlock(
                    block_type="shadow.content.text",
                    content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                    typed_content={"text": output_text},
                )],
                finalized_at=utc_timestamp(),
                source_request_ref=RecordVersionRef(record_id=ids["request"], version=1),
                produced_by_run_ref=RecordVersionRef(record_id=ids["run"], version=1),
            )
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(update={
                "lifecycle": "completed", "result_ref": RecordVersionRef(record_id=ids["message-assistant"], version=1),
                "usage_summary": getattr(output, "usage", None), "terminal_at": utc_timestamp(), "last_event_cursor": "2",
            })
            final_attempt = ExecutionAttemptPayload.model_validate(initial_attempt["typed_payload"]).model_copy(update={
                "lifecycle": "succeeded", "execution_ref": getattr(output, "execution_ref", None) or f"deterministic:{token}",
                "result_ref": RecordVersionRef(record_id=ids["message-assistant"], version=1), "finished_at": utc_timestamp(),
            })
            final_conversation = ConversationPayload(
                title=current_payload.title, conversation_state=current_payload.conversation_state,
                message_refs=current_payload.message_refs + [RecordVersionRef(record_id=ids["message-user"], version=1), RecordVersionRef(record_id=ids["message-assistant"], version=1)],
                queued_run_refs=current_payload.queued_run_refs, foreground_run_ref=StableRecordRef(record_id=ids["run"]), profile_settings=current_payload.profile_settings,
            )
            final_operations = [
                self._operation(
                    f"operation-result-message-{token}", "create", ids["message-assistant"], "shadow.profile.message",
                    f"{PROFILE_SCHEMA}#/$defs/MessagePayload", owner_ref, space_id, self.runtime_descriptor.descriptor_id,
                    assistant_message.model_dump(mode="json", exclude_none=True), final_provenance,
                ),
                self._operation(
                    f"operation-result-attempt-{token}", "update", ids["attempt"], "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload", owner_ref, space_id, principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True), final_provenance, expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-result-run-{token}", "update", ids["run"], "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload", owner_ref, space_id, principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True), final_provenance, expected_version=initial_run["version"],
                ),
                self._operation(
                    f"operation-result-conversation-{token}", "update", conversation_id, "shadow.profile.conversation",
                    f"{PROFILE_SCHEMA}#/$defs/ConversationPayload", owner_ref, space_id, principal_ref,
                    final_conversation.model_dump(mode="json", exclude_none=True), final_provenance, expected_version=initial_conversation["version"],
                ),
            ]
        final_result = self.authority.commit(CommitPlan(
            commit_request_id=f"commit-request-result-{token}", idempotency_scope=f"turn-result:{conversation_id}",
            idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=principal_ref,
            operations=final_operations, prepared_at=utc_timestamp(), correlation_id=f"correlation-{token}",
        ))
        if final_result.outcome in {"failed", "conflict"}:
            raise ShadowDomainError(ShadowError(
                code="shadow.runtime.result-commit-failed", category="unavailable" if final_result.outcome == "failed" else "conflict",
                message="Runtime result could not be durably committed; the dispatch boundary remains recoverable.",
                typed_details=final_result.structured_error, retryable=final_result.outcome == "failed",
            ))
        self.repository.append_event(ids["run"], "shadow.run.unknown" if runtime_failure else "shadow.run.completed", {
            "run_id": ids["run"], "attempt_id": ids["attempt"], "result_message_id": ids["message-assistant"] if not runtime_failure else None,
            "usage": getattr(output, "usage", None) if not runtime_failure else None,
        })
        return TurnResult(
            conversation=self.repository.get(conversation_id) or {},
            run=self.repository.get(ids["run"]) or {},
            user_message=self.repository.get(ids["message-user"]) or {},
            assistant_message=self.repository.get(ids["message-assistant"]) or {},
            admission=self.repository.get(ids["admission"]) or {},
            ephemeral=False,
            replayed=final_result.outcome == "idempotent_replay",
        )

    def retry_run(
        self,
        *,
        run_id: str,
        principal_ref: str,
        idempotency_key: str,
    ) -> TurnResult:
        """Re-execute an existing Request while appending a new Attempt."""
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable; retry was not recorded.",
                    retryable=True,
                )
            )
        run_record = self.repository.get(run_id)
        if not run_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.not-found",
                    category="validation",
                    message=f"Run {run_id} was not found.",
                )
            )
        run_payload = RunPayload.model_validate(run_record["typed_payload"])
        request_record = self.repository.get(run_payload.request_ref.record_id, run_payload.request_ref.version)
        if not request_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.request.not-found",
                    category="internal",
                    message="Run request could not be recovered.",
                )
            )
        request = RequestPayload.model_validate(request_record["typed_payload"])
        if not isinstance(request.work_input, RecordVersionRef):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-input-unsupported",
                    category="unsupported",
                    message="Retry requires a durable message input reference.",
                )
            )
        user_record = self.repository.get(request.work_input.record_id, request.work_input.version)
        if not user_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-input-missing",
                    category="internal",
                    message="Retry input message could not be recovered.",
                )
            )
        user_payload = MessagePayload.model_validate(user_record["typed_payload"])
        block = user_payload.content_blocks[0].typed_content
        text = block.get("text") if isinstance(block, dict) else block
        if not isinstance(text, str) or not text:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-input-invalid",
                    category="validation",
                    message="Retry input message does not contain text.",
                )
            )
        conversation_id = user_payload.conversation_ref.record_id
        conversation = self.repository.get(conversation_id)
        if not conversation:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.conversation.not-found",
                    category="internal",
                    message="Retry conversation could not be recovered.",
                )
            )
        current_payload = ConversationPayload.model_validate(conversation["typed_payload"])
        token = sha256_digest({"run": run_id, "key": idempotency_key})[7:31]
        assistant_id = f"message-assistant-retry-{token}"
        attempt_id = f"attempt-retry-{token}"
        now = utc_timestamp()
        output = self.runtime_adapter.execute(text)
        run_version = run_record["version"] + 1
        assistant_message = MessagePayload(
            conversation_ref=StableRecordRef(record_id=conversation_id),
            sequence=len(current_payload.message_refs) + 1,
            message_type="shadow.message.assistant",
            author_ref=self.runtime_descriptor.descriptor_id,
            content_blocks=[
                ContentBlock(
                    block_type="shadow.content.text",
                    content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                    typed_content={"text": output.text},
                )
            ],
            finalized_at=now,
            source_request_ref=RecordVersionRef(
                record_id=run_payload.request_ref.record_id, version=run_payload.request_ref.version
            ),
            produced_by_run_ref=RecordVersionRef(record_id=run_id, version=run_version),
        )
        if not run_payload.binding_refs:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-binding-missing",
                    category="internal",
                    message="Retry requires the original execution binding.",
                )
            )
        attempt = ExecutionAttemptPayload(
            run_ref=StableRecordRef(record_id=run_id),
            binding_ref=run_payload.binding_refs[0],
            lifecycle="succeeded",
            attempt_number=len(run_payload.attempt_refs) + 1,
            execution_ref=f"deterministic:{token}",
            result_ref=RecordVersionRef(record_id=assistant_id, version=1),
            started_at=now,
            finished_at=now,
        )
        updated_run = RunPayload(
            request_ref=run_payload.request_ref,
            lifecycle="completed",
            requirements_ref=run_payload.requirements_ref,
            binding_refs=run_payload.binding_refs,
            attempt_refs=run_payload.attempt_refs + [RecordVersionRef(record_id=attempt_id, version=1)],
            active_attempt_ref=StableRecordRef(record_id=attempt_id),
            result_ref=RecordVersionRef(record_id=assistant_id, version=1),
            usage_summary=output.usage,
            started_at=run_payload.started_at or now,
            terminal_at=now,
            last_event_cursor=run_payload.last_event_cursor,
        )
        updated_conversation = ConversationPayload(
            title=current_payload.title,
            conversation_state=current_payload.conversation_state,
            message_refs=current_payload.message_refs + [RecordVersionRef(record_id=assistant_id, version=1)],
            queued_run_refs=current_payload.queued_run_refs,
            foreground_run_ref=StableRecordRef(record_id=run_id),
            profile_settings=current_payload.profile_settings,
        )
        provenance = Provenance(origin_type="shadow.origin.user-command", origin_ref=f"retry-{token}")
        owner_ref = conversation["owner_ref"]
        space_id = conversation["space_id"]
        operations = [
            self._operation(
                f"operation-{assistant_id}",
                "create",
                assistant_id,
                "shadow.profile.message",
                f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
                owner_ref,
                space_id,
                self.runtime_descriptor.descriptor_id,
                assistant_message.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{attempt_id}",
                "create",
                attempt_id,
                "shadow.kernel.execution-attempt",
                f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                owner_ref,
                space_id,
                principal_ref,
                attempt.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-update-{run_id}-{token}",
                "update",
                run_id,
                "shadow.kernel.run",
                f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                owner_ref,
                space_id,
                principal_ref,
                updated_run.model_dump(mode="json", exclude_none=True),
                provenance,
                expected_version=run_record["version"],
            ),
            self._operation(
                f"operation-conversation-retry-{token}",
                "update",
                conversation_id,
                "shadow.profile.conversation",
                f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
                owner_ref,
                space_id,
                principal_ref,
                updated_conversation.model_dump(mode="json", exclude_none=True),
                provenance,
                expected_version=conversation["version"],
            ),
        ]
        plan = CommitPlan(
            commit_request_id=f"commit-request-retry-{token}",
            idempotency_scope=f"retry:{run_id}",
            idempotency_key=idempotency_key,
            request_digest=sha256_digest({"run_id": run_id, "text": text}),
            actor_ref=principal_ref,
            operations=operations,
            prepared_at=now,
            correlation_id=f"correlation-retry-{token}",
            causation_id=run_payload.request_ref.record_id,
        )
        result = self.authority.commit(plan)
        if result.outcome in {"failed", "conflict"}:
            category = "conflict" if result.outcome == "conflict" else "validation"
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-commit-failed",
                    category=category,
                    message="Retry could not append a new Attempt.",
                    typed_details=result.model_dump(mode="json", exclude_none=True),
                )
            )
        if result.outcome != "idempotent_replay":
            self.repository.append_event(
                run_id, "shadow.run.started", {"run_id": run_id, "attempt_id": attempt_id}
            )
            self.repository.append_event(
                run_id,
                "shadow.run.completed",
                {"run_id": run_id, "result_message_id": assistant_id, "usage": output.usage},
            )
        return TurnResult(
            conversation=self.repository.get(conversation_id) or {},
            run=self.repository.get(run_id) or {},
            user_message=user_record,
            assistant_message=self.repository.get(assistant_id) or {},
            admission=self.repository.get(
                request.admission_ref.record_id, request.admission_ref.version
            )
            or {},
            ephemeral=False,
            replayed=result.outcome == "idempotent_replay",
        )

    def _ensure_runtime_descriptor(self) -> AdapterDescriptor:
        body = self.runtime_adapter.describe()
        descriptor = AdapterDescriptor(**body, descriptor_digest=sha256_digest(body))
        if not descriptor.supported_target_kinds:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.descriptor-no-target-kind",
                    category="incompatible",
                    message="A Runtime Adapter must declare at least one target kind.",
                )
            )
        self.adapters.register(descriptor)
        legacy_default = (
            descriptor.descriptor_id == "shadow.adapter.deterministic"
            and descriptor.descriptor_version == "1.0.0"
        )
        operation_id = "operation-adapter-deterministic" if legacy_default else f"operation-{descriptor.descriptor_id}"
        commit_request_id = (
            "commit-request-adapter-deterministic"
            if legacy_default
            else f"commit-request-{descriptor.descriptor_id}"
        )
        idempotency_key = (
            "deterministic-v1"
            if legacy_default
            else f"{descriptor.descriptor_id}:{descriptor.descriptor_version}"
        )
        operation = self._operation(
            operation_id,
            "create",
            descriptor.descriptor_id,
            "shadow.adapter.descriptor",
            f"{ADAPTER_SCHEMA}#/$defs/AdapterDescriptor",
            "system",
            "system",
            "system",
            descriptor.model_dump(mode="json", exclude_none=True),
            Provenance(origin_type="shadow.origin.system", origin_ref="phase0-bootstrap"),
        )
        plan = CommitPlan(
            commit_request_id=commit_request_id,
            idempotency_scope="system-adapter",
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(descriptor.model_dump(mode="json", exclude_none=True)),
            actor_ref="system",
            operations=[operation],
            prepared_at=utc_timestamp(),
        )
        result = self.authority.commit(plan)
        if result.outcome in {"failed", "conflict"}:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.descriptor-commit-failed",
                    category="validation" if result.outcome == "failed" else "conflict",
                    message="Runtime Adapter descriptor could not be committed.",
                    typed_details=result.model_dump(mode="json", exclude_none=True),
                )
            )
        return descriptor

    @staticmethod
    def _operation(
        operation_id: str,
        operation: str,
        record_id: str,
        record_type: str,
        target_schema_ref: str,
        owner_ref: str,
        space_id: str,
        created_by: str,
        typed_payload: dict[str, Any],
        provenance: Provenance,
        expected_version: int | None = None,
    ) -> CommitOperation:
        return CommitOperation(
            operation_id=operation_id,
            operation=operation,
            record_id=record_id,
            record_type=record_type,
            target_schema_ref=target_schema_ref,
            owner_ref=owner_ref,
            space_id=space_id,
            created_by=created_by,
            data_classification="personal",
            provenance=provenance,
            retention_policy_ref=RETENTION_REF,
            typed_payload=typed_payload,
            expected_version=expected_version,
        )
