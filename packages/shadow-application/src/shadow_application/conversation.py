from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shadow_kernel.adapters import AdapterDescriptor, AdapterRegistry
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.dispatch import DispatchResult, ExecutionDispatcher
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import (
    AdmissionRecordPayload,
    CapabilityEnvelopeSnapshot,
    CommitOperation,
    CommitPlan,
    ContentBlock,
    ConversationPayload,
    ExecutionAttemptPayload,
    ExecutionRequest,
    ExecutionRequirementsPayload,
    MessagePayload,
    Provenance,
    RecordVersionRef,
    RequestPayload,
    RunPayload,
    StableRecordRef,
)
from shadow_kernel.repository import CanonicalRepository
from shadow_kernel.runtime import RuntimeAdapter

from .execution import DurableFinalization, ExecutionCoordinator

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
        runtime_adapter: RuntimeAdapter,
    ):
        self.repository = repository
        self.authority = authority
        self.adapters = AdapterRegistry()
        self.runtime_adapter = runtime_adapter
        self.coordinator = ExecutionCoordinator(
            repository,
            authority,
            ExecutionDispatcher(self.adapters),
        )
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
        plan = CommitPlan(
            commit_request_id=f"commit-request-{record_id}",
            idempotency_scope=f"conversation:{owner_ref}:{space_id}",
            idempotency_key=idempotency_key,
            request_digest=sha256_digest(payload.model_dump(mode="json", exclude_none=True)),
            actor_ref=owner_ref,
            operations=[operation],
            prepared_at=utc_timestamp(),
        )
        result = self.authority.commit(plan)
        if result.outcome == "failed":
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.conversation.create-failed",
                    category="validation",
                    message="Conversation creation failed.",
                    typed_details=result.structured_error,
                )
            )
        record = self.repository.get(record_id)
        if record is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.record-missing",
                    category="internal",
                    message="Committed conversation could not be read back.",
                )
            )
        return record

    def install_runtime_adapter(self, runtime_adapter: RuntimeAdapter) -> AdapterDescriptor:
        """Select a healthy Runtime through the generic Adapter boundary."""
        self.runtime_adapter = runtime_adapter
        self.runtime_descriptor = self._ensure_runtime_descriptor()
        self.runtime_target_kind = self.runtime_descriptor.supported_target_kinds[0]
        return self.runtime_descriptor

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self.repository.get(conversation_id)

    def list_conversations(
        self, owner_ref: str | None = None, space_id: str | None = None
    ) -> list[dict[str, Any]]:
        return self.repository.query(
            owner_refs={owner_ref} if owner_ref else None,
            space_ids={space_id} if space_id else None,
            record_types={"shadow.profile.conversation"},
            record_states={"active"},
        )

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        conversation = self.repository.get(conversation_id)
        if not conversation:
            return []
        return [
            self.repository.get(ref["record_id"], ref["version"])
            for ref in conversation["typed_payload"]["message_refs"]
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self.repository.get(run_id)

    def submit_turn(
        self,
        *,
        conversation_id: str,
        principal_ref: str,
        endpoint_ref: str = "endpoint-local-web",
        text: str,
        idempotency_key: str,
    ) -> TurnResult:
        if not self.repository.available:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.unavailable",
                    category="unavailable",
                    message="Canonical Repository is unavailable; this request must be retried as ephemeral only.",
                    retryable=True,
                )
            )
        conversation = self.repository.get(conversation_id)
        if not conversation:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.conversation.not-found",
                    category="validation",
                    message=f"Conversation {conversation_id} was not found.",
                )
            )
        token = sha256_digest({"conversation": conversation_id, "key": idempotency_key})[7:31]
        ids = {
            name: f"{name}-{token}"
            for name in (
                "message-user",
                "message-assistant",
                "admission",
                "request",
                "requirements",
                "run",
                "attempt",
                "binding",
                "capability-envelope",
            )
        }
        now = utc_timestamp()
        request_digest = sha256_digest({"conversation_id": conversation_id, "text": text})
        prior = self.repository.idempotency_result(f"turn:{conversation_id}", idempotency_key)
        if prior is not None and prior.get("request_digest") != request_digest:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.repository.idempotency-mismatch",
                    category="conflict",
                    message="The idempotency key was already used for a different conversation turn.",
                )
            )
        current_payload = ConversationPayload.model_validate(conversation["typed_payload"])
        owner_ref = conversation["owner_ref"]
        space_id = conversation["space_id"]
        if prior is not None:
            return TurnResult(
                conversation=self.repository.get(conversation_id) or {},
                run=self.repository.get(ids["run"]) or {},
                user_message=self.repository.get(ids["message-user"]) or {},
                assistant_message=self.repository.get(ids["message-assistant"]) or {},
                admission=self.repository.get(ids["admission"]) or {},
                ephemeral=False,
                replayed=True,
            )
        user_message = MessagePayload(
            conversation_ref=StableRecordRef(record_id=conversation_id),
            sequence=len(current_payload.message_refs) + 1,
            message_type="shadow.message.user",
            author_ref=principal_ref,
            content_blocks=[
                ContentBlock(
                    block_type="shadow.content.text",
                    content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                    typed_content={"text": text},
                )
            ],
            finalized_at=now,
        )
        admission = AdmissionRecordPayload(
            admission_id=ids["admission"],
            submission_id=f"submission-{token}",
            input_type="shadow.input.conversation-turn",
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            space_id=space_id,
            request_digest=sha256_digest({"conversation_id": conversation_id, "text": text}),
            decision="accepted",
            request_ref=StableRecordRef(record_id=ids["request"]),
            root_run_ref=StableRecordRef(record_id=ids["run"]),
            decided_at=now,
            retention_policy_ref=RETENTION_REF,
        )
        requirements = ExecutionRequirementsPayload(
            requirements_id=ids["requirements"],
            required_capabilities=[],
            acceptable_target_kinds=[self.runtime_target_kind],
            allowed_side_effects=[],
            streaming_required=True,
            checkpoint_required=False,
            created_from=RecordVersionRef(record_id=ids["admission"], version=1),
        )
        request = RequestPayload(
            admission_ref=RecordVersionRef(record_id=ids["admission"], version=1),
            request_type="shadow.request.conversation-turn",
            work_input=RecordVersionRef(record_id=ids["message-user"], version=1),
            requirements_ref=RecordVersionRef(record_id=ids["requirements"], version=1),
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            accepted_at=now,
            correlation_id=f"correlation-{token}",
        )
        cap = {
            "envelope_id": ids["capability-envelope"],
            "principal_ref": principal_ref,
            "grantee_ref": self.runtime_descriptor.descriptor_id,
            "scope_ref": {"record_id": ids["run"]},
            "allowed_capabilities": [],
            "data_scope": {
                "allowed_space_ids": [space_id],
                "allowed_record_types": [],
                "maximum_classification": "personal",
                "external_source_refs": [],
            },
            "resource_scope": {"allowed_resource_refs": [], "allowed_operations": []},
            "budget_limits": [],
            "allowed_side_effects": [],
            "approval_refs": [],
            "policy_ref": {"record_id": "policy-default"},
            "policy_version": 1,
            "valid_from": now,
            "valid_until": now,
            "state": "active",
            "issued_at": now,
        }
        binding = self.adapters.bind(
            descriptor_id=self.runtime_descriptor.descriptor_id,
            target_kind=self.runtime_target_kind,
            required_capabilities=[],
            binding_id=ids["binding"],
            scope_ref={"record_id": ids["run"]},
            capability_envelope_ref={"record_id": ids["capability-envelope"], "version": 1},
            selection_source_ref={"record_id": ids["request"]},
        )
        run = RunPayload(
            request_ref=RecordVersionRef(record_id=ids["request"], version=1),
            lifecycle="running",
            requirements_ref=RecordVersionRef(record_id=ids["requirements"], version=1),
            binding_refs=[RecordVersionRef(record_id=ids["binding"], version=1)],
            attempt_refs=[RecordVersionRef(record_id=ids["attempt"], version=1)],
            active_attempt_ref=StableRecordRef(record_id=ids["attempt"]),
            result_ref=None,
            usage_summary=None,
            started_at=now,
            terminal_at=None,
            last_event_cursor=None,
        )
        attempt = ExecutionAttemptPayload(
            run_ref=StableRecordRef(record_id=ids["run"]),
            binding_ref=RecordVersionRef(record_id=ids["binding"], version=1),
            lifecycle="dispatching",
            attempt_number=1,
            execution_ref=None,
            result_ref=None,
            started_at=now,
            finished_at=None,
        )
        new_refs = current_payload.message_refs + [
            RecordVersionRef(record_id=ids["message-user"], version=1),
        ]
        conversation_update = ConversationPayload(
            title=current_payload.title,
            conversation_state=current_payload.conversation_state,
            message_refs=new_refs,
            queued_run_refs=current_payload.queued_run_refs,
            foreground_run_ref=StableRecordRef(record_id=ids["run"]),
            profile_settings=current_payload.profile_settings,
        )
        provenance = Provenance(
            origin_type="shadow.origin.user-command", origin_ref=f"submission-{token}"
        )
        operations = [
            self._operation(
                f"operation-{ids['message-user']}",
                "create",
                ids["message-user"],
                "shadow.profile.message",
                f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
                owner_ref,
                space_id,
                principal_ref,
                user_message.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['admission']}",
                "create",
                ids["admission"],
                "shadow.kernel.admission",
                f"{KERNEL_SCHEMA}#/$defs/AdmissionRecordPayload",
                owner_ref,
                space_id,
                principal_ref,
                admission.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['requirements']}",
                "create",
                ids["requirements"],
                "shadow.kernel.execution-requirements",
                f"{KERNEL_SCHEMA}#/$defs/ExecutionRequirementsPayload",
                owner_ref,
                space_id,
                principal_ref,
                requirements.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['request']}",
                "create",
                ids["request"],
                "shadow.kernel.request",
                f"{KERNEL_SCHEMA}#/$defs/RequestPayload",
                owner_ref,
                space_id,
                principal_ref,
                request.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['run']}",
                "create",
                ids["run"],
                "shadow.kernel.run",
                f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                owner_ref,
                space_id,
                principal_ref,
                run.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['attempt']}",
                "create",
                ids["attempt"],
                "shadow.kernel.execution-attempt",
                f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                owner_ref,
                space_id,
                principal_ref,
                attempt.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-{ids['capability-envelope']}",
                "create",
                ids["capability-envelope"],
                "shadow.adapter.capability-envelope",
                f"{ADAPTER_SCHEMA}#/$defs/CapabilityEnvelopePayload",
                owner_ref,
                space_id,
                principal_ref,
                cap,
                provenance,
            ),
            self._operation(
                f"operation-{ids['binding']}",
                "create",
                ids["binding"],
                "shadow.adapter.execution-binding",
                f"{ADAPTER_SCHEMA}#/$defs/ExecutionBindingPayload",
                owner_ref,
                space_id,
                principal_ref,
                binding.model_dump(mode="json", exclude_none=True),
                provenance,
            ),
            self._operation(
                f"operation-conversation-{token}",
                "update",
                conversation_id,
                "shadow.profile.conversation",
                f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
                owner_ref,
                space_id,
                principal_ref,
                conversation_update.model_dump(mode="json", exclude_none=True),
                provenance,
                expected_version=conversation["version"],
            ),
        ]
        plan = CommitPlan(
            commit_request_id=f"commit-request-turn-{token}",
            idempotency_scope=f"turn:{conversation_id}",
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            actor_ref=principal_ref,
            operations=operations,
            prepared_at=now,
            correlation_id=f"correlation-{token}",
        )
        execution_request = ExecutionRequest(
            execution_request_id=f"execution-request-{token}",
            run_ref=RecordVersionRef(record_id=ids["run"], version=1),
            attempt_ref=RecordVersionRef(record_id=ids["attempt"], version=1),
            binding_ref=RecordVersionRef(record_id=ids["binding"], version=1),
            idempotency_key=idempotency_key,
            capability_envelope_snapshot=CapabilityEnvelopeSnapshot(
                envelope_ref=StableRecordRef(record_id=ids["capability-envelope"]),
                version=1,
                digest=sha256_digest(cap),
                effective_constraints={"allowed_space_ids": [space_id], "allowed_side_effects": []},
            ),
            input_schema_ref=f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
            typed_input={"text": text},
            correlation_id=f"correlation-{token}",
            submitted_at=now,
        )
        durable = self.coordinator.execute_durable(
            initial_plan=plan,
            request=execution_request,
            target_kind=self.runtime_target_kind,
            run_id=ids["run"],
            attempt_id=ids["attempt"],
            idempotency_scope=f"turn:{conversation_id}",
            finalize=lambda dispatch, failure: self._finalize_turn(
                dispatch=dispatch,
                failure=failure,
                token=token,
                ids=ids,
                conversation_id=conversation_id,
                current_payload=current_payload,
                owner_ref=owner_ref,
                space_id=space_id,
                principal_ref=principal_ref,
                request_digest=request_digest,
                idempotency_key=idempotency_key,
            ),
        )
        if durable.replayed:
            return TurnResult(
                conversation=self.repository.get(conversation_id) or {},
                run=self.repository.get(ids["run"]) or {},
                user_message=self.repository.get(ids["message-user"]) or {},
                assistant_message=self.repository.get(ids["message-assistant"]) or {},
                admission=self.repository.get(ids["admission"]) or {},
                ephemeral=False,
                replayed=True,
            )
        return TurnResult(
            conversation=self.repository.get(conversation_id) or {},
            run=self.repository.get(ids["run"]) or {},
            user_message=self.repository.get(ids["message-user"]) or {},
            assistant_message=self.repository.get(ids["message-assistant"]) or {},
            admission=self.repository.get(ids["admission"]) or {},
            ephemeral=False,
            replayed=bool(durable.final_commit and durable.final_commit.outcome == "idempotent_replay"),
        )

    def _finalize_turn(
        self,
        *,
        dispatch: DispatchResult | None,
        failure: dict[str, Any] | None,
        token: str,
        ids: dict[str, str],
        conversation_id: str,
        current_payload: ConversationPayload,
        owner_ref: str,
        space_id: str,
        principal_ref: str,
        request_digest: str,
        idempotency_key: str,
    ) -> DurableFinalization:
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
        output = dispatch.output if dispatch is not None else None
        output_text = getattr(output, "text", None)
        runtime_failure = failure
        if runtime_failure is None and not isinstance(output_text, str):
            runtime_failure = {
                "code": "shadow.runtime.outcome-unknown",
                "reason": "Runtime Adapter result did not contain text.",
            }
        final_provenance = Provenance(
            origin_type="shadow.origin.runtime-result", origin_ref=f"result-{token}"
        )
        if runtime_failure is not None:
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(
                update={
                    "lifecycle": "waiting",
                    "failure_summary": runtime_failure,
                    "terminal_at": None,
                }
            )
            final_attempt = ExecutionAttemptPayload.model_validate(
                initial_attempt["typed_payload"]
            ).model_copy(
                update={
                    "lifecycle": "outcome_unknown",
                    "failure_summary": runtime_failure,
                    "finished_at": None,
                }
            )
            final_operations = [
                self._operation(
                    f"operation-result-attempt-{token}",
                    "update",
                    ids["attempt"],
                    "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                    expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-result-run-{token}",
                    "update",
                    ids["run"],
                    "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                    expected_version=initial_run["version"],
                ),
            ]
            result_message_id: str | None = None
            event_type = "shadow.run.unknown"
            usage: dict[str, Any] | None = None
        else:
            assistant_message = MessagePayload(
                conversation_ref=StableRecordRef(record_id=conversation_id),
                sequence=len(current_payload.message_refs) + 2,
                message_type="shadow.message.assistant",
                author_ref=self.runtime_descriptor.descriptor_id,
                content_blocks=[
                    ContentBlock(
                        block_type="shadow.content.text",
                        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                        typed_content={"text": output_text},
                    )
                ],
                finalized_at=utc_timestamp(),
                source_request_ref=RecordVersionRef(record_id=ids["request"], version=1),
                produced_by_run_ref=RecordVersionRef(record_id=ids["run"], version=1),
            )
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(
                update={
                    "lifecycle": "completed",
                    "result_ref": RecordVersionRef(record_id=ids["message-assistant"], version=1),
                    "usage_summary": getattr(output, "usage", None),
                    "terminal_at": utc_timestamp(),
                    "last_event_cursor": "2",
                }
            )
            final_attempt = ExecutionAttemptPayload.model_validate(
                initial_attempt["typed_payload"]
            ).model_copy(
                update={
                    "lifecycle": "succeeded",
                    "execution_ref": getattr(output, "execution_ref", None)
                    or f"deterministic:{token}",
                    "result_ref": RecordVersionRef(record_id=ids["message-assistant"], version=1),
                    "finished_at": utc_timestamp(),
                }
            )
            final_conversation = ConversationPayload(
                title=current_payload.title,
                conversation_state=current_payload.conversation_state,
                message_refs=current_payload.message_refs
                + [
                    RecordVersionRef(record_id=ids["message-user"], version=1),
                    RecordVersionRef(record_id=ids["message-assistant"], version=1),
                ],
                queued_run_refs=current_payload.queued_run_refs,
                foreground_run_ref=StableRecordRef(record_id=ids["run"]),
                profile_settings=current_payload.profile_settings,
            )
            final_operations = [
                self._operation(
                    f"operation-result-message-{token}",
                    "create",
                    ids["message-assistant"],
                    "shadow.profile.message",
                    f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
                    owner_ref,
                    space_id,
                    self.runtime_descriptor.descriptor_id,
                    assistant_message.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                ),
                self._operation(
                    f"operation-result-attempt-{token}",
                    "update",
                    ids["attempt"],
                    "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                    expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-result-run-{token}",
                    "update",
                    ids["run"],
                    "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                    expected_version=initial_run["version"],
                ),
                self._operation(
                    f"operation-result-conversation-{token}",
                    "update",
                    conversation_id,
                    "shadow.profile.conversation",
                    f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_conversation.model_dump(mode="json", exclude_none=True),
                    final_provenance,
                    expected_version=initial_conversation["version"],
                ),
            ]
            result_message_id = ids["message-assistant"]
            event_type = "shadow.run.completed"
            usage = getattr(output, "usage", None)
        return DurableFinalization(
            plan=CommitPlan(
                commit_request_id=f"commit-request-result-{token}",
                idempotency_scope=f"turn-result:{conversation_id}",
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                actor_ref=principal_ref,
                operations=final_operations,
                prepared_at=utc_timestamp(),
                correlation_id=f"correlation-{token}",
            ),
            event_type=event_type,
            event_payload={
                "run_id": ids["run"],
                "attempt_id": ids["attempt"],
                "result_message_id": result_message_id,
                "usage": usage,
            },
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
        prior_retry = self.repository.idempotency_result(f"retry:{run_id}", idempotency_key)
        if prior_retry is not None:
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
                replayed=True,
            )
        now = utc_timestamp()
        return self._retry_run_coordinated(
            run_id=run_id,
            principal_ref=principal_ref,
            idempotency_key=idempotency_key,
            run_record=run_record,
            run_payload=run_payload,
            request=request,
            user_record=user_record,
            text=text,
            conversation_id=conversation_id,
            conversation=conversation,
            current_payload=current_payload,
            token=token,
            assistant_id=assistant_id,
            attempt_id=attempt_id,
            now=now,
        )
        # Legacy retry path retained below until R6 removes the parallel v0.1
        # implementation.  The coordinator path above is the active path.
        if not run_payload.binding_refs:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-binding-missing",
                    category="internal",
                    message="Retry requires the original execution binding.",
                )
            )
        binding_record = self.repository.get(run_payload.binding_refs[0].record_id)
        if not binding_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-binding-missing",
                    category="internal",
                    message="Retry binding could not be recovered.",
                )
            )
        cap_ref = binding_record["typed_payload"].get("capability_envelope_ref", {})
        cap_record = self.repository.get(cap_ref.get("record_id")) if cap_ref.get("record_id") else None
        if not cap_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-capability-envelope-missing",
                    category="internal",
                    message="Retry capability envelope could not be recovered.",
                )
            )
        execution_request = ExecutionRequest(
            execution_request_id=f"execution-request-{token}",
            run_ref=RecordVersionRef(record_id=run_id, version=run_record["version"]),
            attempt_ref=RecordVersionRef(record_id=attempt_id, version=1),
            binding_ref=run_payload.binding_refs[0],
            idempotency_key=idempotency_key,
            capability_envelope_snapshot=CapabilityEnvelopeSnapshot(
                envelope_ref=StableRecordRef(record_id=cap_record["record_id"]),
                version=cap_record["version"],
                digest=sha256_digest(cap_record["typed_payload"]),
                effective_constraints={},
            ),
            input_schema_ref=f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
            typed_input={"text": text},
            correlation_id=f"correlation-{token}",
            submitted_at=now,
        )
        dispatch_result = self.coordinator.execute(
            execution_request,
            target_kind=self.runtime_target_kind,
            idempotency_scope=f"retry:{run_id}",
        )
        output = dispatch_result.output
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

    def _retry_run_coordinated(
        self,
        *,
        run_id: str,
        principal_ref: str,
        idempotency_key: str,
        run_record: dict[str, Any],
        run_payload: RunPayload,
        request: RequestPayload,
        user_record: dict[str, Any],
        text: str,
        conversation_id: str,
        conversation: dict[str, Any],
        current_payload: ConversationPayload,
        token: str,
        assistant_id: str,
        attempt_id: str,
        now: str,
    ) -> TurnResult:
        if not run_payload.binding_refs:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-binding-missing",
                    category="internal",
                    message="Retry requires the original execution binding.",
                )
            )
        binding_record = self.repository.get(run_payload.binding_refs[0].record_id)
        if not binding_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-binding-missing",
                    category="internal",
                    message="Retry binding could not be recovered.",
                )
            )
        cap_ref = binding_record["typed_payload"].get("capability_envelope_ref", {})
        cap_record = self.repository.get(cap_ref.get("record_id")) if cap_ref.get("record_id") else None
        if not cap_record:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.run.retry-capability-envelope-missing",
                    category="internal",
                    message="Retry capability envelope could not be recovered.",
                )
            )
        owner_ref = conversation["owner_ref"]
        space_id = conversation["space_id"]
        attempt = ExecutionAttemptPayload(
            run_ref=StableRecordRef(record_id=run_id),
            binding_ref=run_payload.binding_refs[0],
            lifecycle="dispatching",
            attempt_number=len(run_payload.attempt_refs) + 1,
            execution_ref=None,
            result_ref=None,
            started_at=now,
            finished_at=None,
        )
        prepared_run = RunPayload.model_validate(run_record["typed_payload"]).model_copy(
            update={
                "lifecycle": "running",
                "attempt_refs": run_payload.attempt_refs
                + [RecordVersionRef(record_id=attempt_id, version=1)],
                "active_attempt_ref": StableRecordRef(record_id=attempt_id),
                "result_ref": None,
                "failure_summary": None,
                "terminal_at": None,
            }
        )
        provenance = Provenance(origin_type="shadow.origin.user-command", origin_ref=f"retry-{token}")
        initial_operations = [
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
                prepared_run.model_dump(mode="json", exclude_none=True),
                provenance,
                expected_version=run_record["version"],
            ),
        ]
        request_digest = sha256_digest({"run_id": run_id, "text": text})
        initial_plan = CommitPlan(
            commit_request_id=f"commit-request-retry-{token}",
            idempotency_scope=f"retry:{run_id}",
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            actor_ref=principal_ref,
            operations=initial_operations,
            prepared_at=now,
            correlation_id=f"correlation-retry-{token}",
            causation_id=run_payload.request_ref.record_id,
        )
        execution_request = ExecutionRequest(
            execution_request_id=f"execution-request-{token}",
            run_ref=RecordVersionRef(record_id=run_id, version=run_record["version"] + 1),
            attempt_ref=RecordVersionRef(record_id=attempt_id, version=1),
            binding_ref=run_payload.binding_refs[0],
            idempotency_key=idempotency_key,
            capability_envelope_snapshot=CapabilityEnvelopeSnapshot(
                envelope_ref=StableRecordRef(record_id=cap_record["record_id"]),
                version=cap_record["version"],
                digest=sha256_digest(cap_record["typed_payload"]),
                effective_constraints={},
            ),
            input_schema_ref=f"{PROFILE_SCHEMA}#/$defs/MessagePayload",
            typed_input={"text": text},
            correlation_id=f"correlation-{token}",
            submitted_at=now,
        )
        durable = self.coordinator.execute_durable(
            initial_plan=initial_plan,
            request=execution_request,
            target_kind=self.runtime_target_kind,
            run_id=run_id,
            attempt_id=attempt_id,
            idempotency_scope=f"retry-dispatch:{run_id}",
            finalize=lambda dispatch, failure: self._finalize_retry(
                dispatch=dispatch,
                failure=failure,
                run_id=run_id,
                principal_ref=principal_ref,
                idempotency_key=idempotency_key,
                run_record=run_record,
                run_payload=run_payload,
                request=request,
                user_record=user_record,
                conversation_id=conversation_id,
                conversation=conversation,
                current_payload=current_payload,
                token=token,
                assistant_id=assistant_id,
                attempt_id=attempt_id,
                now=now,
            ),
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
            replayed=durable.replayed
            or bool(durable.final_commit and durable.final_commit.outcome == "idempotent_replay"),
        )

    def _finalize_retry(
        self,
        *,
        dispatch: DispatchResult | None,
        failure: dict[str, Any] | None,
        run_id: str,
        principal_ref: str,
        idempotency_key: str,
        run_record: dict[str, Any],
        run_payload: RunPayload,
        request: RequestPayload,
        user_record: dict[str, Any],
        conversation_id: str,
        conversation: dict[str, Any],
        current_payload: ConversationPayload,
        token: str,
        assistant_id: str,
        attempt_id: str,
        now: str,
    ) -> DurableFinalization:
        del user_record
        initial_run = self.repository.get(run_id)
        initial_attempt = self.repository.get(attempt_id)
        if initial_run is None or initial_attempt is None:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.dispatch-boundary-missing",
                    category="internal",
                    message="Retry durable records could not be recovered.",
                )
            )
        output = dispatch.output if dispatch is not None else None
        output_text = getattr(output, "text", None)
        runtime_failure = failure
        if runtime_failure is None and not isinstance(output_text, str):
            runtime_failure = {
                "code": "shadow.runtime.outcome-unknown",
                "reason": "Runtime Adapter result did not contain text.",
            }
        provenance = Provenance(origin_type="shadow.origin.runtime-result", origin_ref=f"retry-result-{token}")
        owner_ref = conversation["owner_ref"]
        space_id = conversation["space_id"]
        if runtime_failure is not None:
            final_attempt = ExecutionAttemptPayload.model_validate(
                initial_attempt["typed_payload"]
            ).model_copy(
                update={
                    "lifecycle": "outcome_unknown",
                    "failure_summary": runtime_failure,
                    "finished_at": None,
                }
            )
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(
                update={
                    "lifecycle": "waiting",
                    "failure_summary": runtime_failure,
                    "terminal_at": None,
                }
            )
            operations = [
                self._operation(
                    f"operation-retry-result-attempt-{token}",
                    "update",
                    attempt_id,
                    "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True),
                    provenance,
                    expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-retry-result-run-{token}",
                    "update",
                    run_id,
                    "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True),
                    provenance,
                    expected_version=initial_run["version"],
                ),
            ]
            event_type = "shadow.run.unknown"
            event_payload = {"run_id": run_id, "attempt_id": attempt_id, "result_message_id": None}
        else:
            final_attempt = ExecutionAttemptPayload.model_validate(
                initial_attempt["typed_payload"]
            ).model_copy(
                update={
                    "lifecycle": "succeeded",
                    "execution_ref": getattr(output, "execution_ref", None)
                    or f"deterministic:{token}",
                    "result_ref": RecordVersionRef(record_id=assistant_id, version=1),
                    "finished_at": now,
                }
            )
            assistant_message = MessagePayload(
                conversation_ref=StableRecordRef(record_id=conversation_id),
                sequence=len(current_payload.message_refs) + 1,
                message_type="shadow.message.assistant",
                author_ref=self.runtime_descriptor.descriptor_id,
                content_blocks=[
                    ContentBlock(
                        block_type="shadow.content.text",
                        content_schema_ref="https://schemas.openshadow.dev/content/text/1.0.0",
                        typed_content={"text": output_text},
                    )
                ],
                finalized_at=now,
                source_request_ref=RecordVersionRef(
                    record_id=run_payload.request_ref.record_id,
                    version=run_payload.request_ref.version,
                ),
                produced_by_run_ref=RecordVersionRef(
                    record_id=run_id, version=initial_run["version"]
                ),
            )
            final_run = RunPayload.model_validate(initial_run["typed_payload"]).model_copy(
                update={
                    "lifecycle": "completed",
                    "result_ref": RecordVersionRef(record_id=assistant_id, version=1),
                    "usage_summary": getattr(output, "usage", None),
                    "terminal_at": now,
                }
            )
            final_conversation = ConversationPayload(
                title=current_payload.title,
                conversation_state=current_payload.conversation_state,
                message_refs=current_payload.message_refs
                + [RecordVersionRef(record_id=assistant_id, version=1)],
                queued_run_refs=current_payload.queued_run_refs,
                foreground_run_ref=StableRecordRef(record_id=run_id),
                profile_settings=current_payload.profile_settings,
            )
            operations = [
                self._operation(
                    f"operation-retry-result-message-{token}",
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
                    f"operation-retry-result-attempt-{token}",
                    "update",
                    attempt_id,
                    "shadow.kernel.execution-attempt",
                    f"{KERNEL_SCHEMA}#/$defs/ExecutionAttemptPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_attempt.model_dump(mode="json", exclude_none=True),
                    provenance,
                    expected_version=initial_attempt["version"],
                ),
                self._operation(
                    f"operation-retry-result-run-{token}",
                    "update",
                    run_id,
                    "shadow.kernel.run",
                    f"{KERNEL_SCHEMA}#/$defs/RunPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_run.model_dump(mode="json", exclude_none=True),
                    provenance,
                    expected_version=initial_run["version"],
                ),
                self._operation(
                    f"operation-retry-result-conversation-{token}",
                    "update",
                    conversation_id,
                    "shadow.profile.conversation",
                    f"{PROFILE_SCHEMA}#/$defs/ConversationPayload",
                    owner_ref,
                    space_id,
                    principal_ref,
                    final_conversation.model_dump(mode="json", exclude_none=True),
                    provenance,
                    expected_version=conversation["version"],
                ),
            ]
            event_type = "shadow.run.completed"
            event_payload = {
                "run_id": run_id,
                "attempt_id": attempt_id,
                "result_message_id": assistant_id,
                "usage": getattr(output, "usage", None),
            }
        return DurableFinalization(
            plan=CommitPlan(
                commit_request_id=f"commit-request-retry-result-{token}",
                idempotency_scope=f"retry-result:{run_id}",
                idempotency_key=idempotency_key,
                request_digest=sha256_digest({"run_id": run_id, "text": output_text or ""}),
                actor_ref=principal_ref,
                operations=operations,
                prepared_at=utc_timestamp(),
                correlation_id=f"correlation-retry-{token}",
                causation_id=request.admission_ref.record_id,
            ),
            event_type=event_type,
            event_payload=event_payload,
        )

    def _ensure_runtime_descriptor(self) -> AdapterDescriptor:
        descriptor = self.coordinator.dispatcher.register_adapter(self.runtime_adapter)
        if not descriptor.supported_target_kinds:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.runtime.descriptor-no-target-kind",
                    category="incompatible",
                    message="A Runtime Adapter must declare at least one target kind.",
                )
            )
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
