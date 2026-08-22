from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from shadow_kernel.commit import CommitAuthority
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest, utc_timestamp
from shadow_kernel.models import CommitOperation, CommitPlan, Provenance, StableRecordRef
from shadow_kernel.registry import ContractRegistry
from shadow_kernel.repository import CanonicalRepository

CONTINUITY_SCHEMA = "https://schemas.openshadow.dev/contracts/continuity/1.0.0"
TASK_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/TaskPayload"
TASK_PROPOSAL_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/TaskProposalPayload"
TASK_PROPOSAL_RECORD_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/TaskProposalRecordPayload"
CHECKPOINT_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/CheckpointPayload"
TASK_RECORD_TYPE = "shadow.profile.durable-task"
PROPOSAL_RECORD_TYPE = "shadow.proposal"
CHECKPOINT_RECORD_TYPE = "shadow.continuity.checkpoint"
RETENTION_REF = StableRecordRef(record_id="retention-default")


@dataclass(frozen=True, slots=True)
class TaskProposalCandidate:
    proposal_id: str
    submitted_by: str
    owner_ref: str
    space_id: str
    payload: dict[str, Any]


class TaskService:
    """Durable Task/Continuity Profile boundary."""

    def __init__(
        self,
        repository: CanonicalRepository,
        authority: CommitAuthority,
        registry: ContractRegistry,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.registry = registry

    def propose(
        self,
        *,
        submitted_by: str,
        owner_ref: str,
        space_id: str,
        operation: str,
        task_key: str,
        goal: str,
        completion_criteria: Any,
        target_task_id: str | None = None,
        expected_version: int | None = None,
        waiting_condition: Any = None,
        deadline: str | None = None,
        result_ref: dict[str, Any] | None = None,
        failure_summary: Any = None,
        proposal_reason: str | None = None,
    ) -> TaskProposalCandidate:
        if operation == "create" and (target_task_id or expected_version is not None):
            raise _invalid("Task create cannot include a target or expected version.")
        if operation != "create" and (not target_task_id or expected_version is None):
            raise _invalid("Task transition requires target and expected version.")
        if operation != "create":
            self._load_task(
                target_task_id or "",
                owner_ref=owner_ref,
                space_id=space_id,
                expected_version=expected_version,
                require_active=False,
            )
        proposal: dict[str, Any] = {
            "proposed_operation": operation,
            "task_key": task_key,
            "goal": goal,
            "completion_criteria": completion_criteria,
        }
        if target_task_id:
            proposal["target_ref"] = {"record_id": target_task_id}
        if expected_version is not None:
            proposal["expected_version"] = expected_version
        if waiting_condition is not None:
            proposal["waiting_condition"] = waiting_condition
        if deadline is not None:
            proposal["deadline"] = deadline
        if result_ref is not None:
            proposal["result_ref"] = result_ref
        if failure_summary is not None:
            proposal["failure_summary"] = failure_summary
        if proposal_reason:
            proposal["proposal_reason"] = proposal_reason
        self._validate(proposal, TASK_PROPOSAL_SCHEMA)
        proposal_id = f"proposal-{sha256_digest({'owner': owner_ref, 'space': space_id, 'proposal': proposal})[7:39]}"
        return TaskProposalCandidate(proposal_id, submitted_by, owner_ref, space_id, proposal)

    def submit_proposal(
        self, candidate: TaskProposalCandidate, *, idempotency_key: str
    ) -> dict[str, Any]:
        self._require_available()
        payload = {
            "proposal_type": "shadow.durable-task-proposal",
            "status": "pending",
            "proposer_ref": candidate.submitted_by,
            "owner_ref": candidate.owner_ref,
            "space_id": candidate.space_id,
            "proposal": candidate.payload,
        }
        operation = self._proposal_operation(
            operation_id=f"operation-{candidate.proposal_id}-create",
            operation="create",
            proposal_id=candidate.proposal_id,
            owner_ref=candidate.owner_ref,
            space_id=candidate.space_id,
            created_by=candidate.submitted_by,
            typed_payload=payload,
        )
        result = self._commit(
            [operation], candidate.owner_ref, candidate.space_id, idempotency_key,
            sha256_digest(candidate.payload), f"commit-request-{candidate.proposal_id}", candidate.submitted_by,
        )
        return self._record_from_result(result, candidate.proposal_id)

    def accept_proposal(
        self,
        *,
        proposal_id: str,
        proposal_expected_version: int,
        principal_ref: str,
        space_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        proposal_record = self.repository.get(proposal_id)
        if proposal_record is None:
            raise _error("shadow.task.not-found", "Task Proposal was not found.")
        self._assert_boundary(proposal_record, principal_ref, space_id)
        payload = proposal_record.get("typed_payload", {})
        if payload.get("proposal_type") != "shadow.durable-task-proposal":
            raise _invalid("Target record is not a Durable Task Proposal.")
        proposal = payload["proposal"]
        request_digest = sha256_digest(
            {"proposal_id": proposal_id, "proposal": proposal, "expected": proposal_expected_version}
        )
        prior = self.repository.idempotency_result(
            f"task:{principal_ref}:{space_id}", idempotency_key
        )
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise _error(
                    "shadow.repository.idempotency-mismatch",
                    "Task idempotency key was reused with a different request digest.",
                )
            task_result = next(
                (item for item in prior["result"].operation_results if item.record_id != proposal_id), None
            )
            if task_result and task_result.resulting_version:
                return {
                    "decision": "accepted",
                    "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
                    "task_ref": {"record_id": task_result.record_id, "version": task_result.resulting_version},
                    "replayed": True,
                    "record": self.get_task(task_result.record_id, principal_ref, space_id),
                }
        if payload.get("status") != "pending":
            raise _error("shadow.task.invalid-transition", "Task Proposal is no longer pending.", category="conflict")

        target = proposal.get("target_ref")
        task_id = target["record_id"] if target else self._task_id(principal_ref, space_id, proposal["task_key"])
        current = None
        if target:
            current = self._load_task(
                task_id,
                owner_ref=principal_ref,
                space_id=space_id,
                expected_version=proposal["expected_version"],
                require_active=False,
            )
        elif self.repository.get(task_id) is not None:
            raise _error(
                "shadow.repository.expected-version-conflict",
                "A Task already exists for this task key.",
                category="conflict",
            )
        task_payload = self._next_payload(current, proposal)
        task_operation = self._task_operation(
            operation_id=f"operation-{task_id}-{proposal['proposed_operation']}",
            operation="create" if current is None else "update",
            task_id=task_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=task_payload,
            expected_version=proposal.get("expected_version"),
            origin_ref=proposal_id,
        )
        accepted_payload = deepcopy(payload)
        accepted_payload["status"] = "accepted"
        accepted_payload["resulting_task_ref"] = {"record_id": task_id}
        proposal_operation = self._proposal_operation(
            operation_id=f"operation-{proposal_id}-accept",
            operation="update",
            proposal_id=proposal_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=accepted_payload,
            expected_version=proposal_expected_version,
        )
        result = self._commit(
            [proposal_operation, task_operation], principal_ref, space_id, idempotency_key,
            request_digest, f"commit-request-{proposal_id}-accept", principal_ref,
        )
        operation_result = next(item for item in result.operation_results if item.record_id == task_id)
        if operation_result.resulting_version is None:
            raise _error("shadow.repository.record-missing", "Accepted Task has no resulting version.")
        return {
            "decision": "accepted",
            "proposal_ref": {"record_id": proposal_id, "version": proposal_expected_version + 1},
            "task_ref": {"record_id": task_id, "version": operation_result.resulting_version},
            "replayed": result.outcome == "idempotent_replay",
            "record": self.get_task(task_id, principal_ref, space_id),
        }

    def create_checkpoint(
        self,
        *,
        task_id: str,
        expected_task_version: int,
        principal_ref: str,
        space_id: str,
        checkpoint_kind: str,
        checkpoint_digest: str,
        runtime_target_kind: str,
        runtime_capabilities: list[str],
        artifact_refs: list[dict[str, Any]],
        native_resume: bool,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_available()
        if checkpoint_kind == "native" and not native_resume:
            raise _error(
                "shadow.continuity.capability-unsupported",
                "Native checkpoint requires native_resume capability.",
            )
        request_digest = sha256_digest(
            {
                "task_id": task_id,
                "expected_version": expected_task_version,
                "checkpoint_kind": checkpoint_kind,
                "checkpoint_digest": checkpoint_digest,
                "runtime_target_kind": runtime_target_kind,
                "runtime_capabilities": runtime_capabilities,
                "artifact_refs": artifact_refs,
                "native_resume": native_resume,
            }
        )
        prior = self.repository.idempotency_result(
            f"task:{principal_ref}:{space_id}", idempotency_key
        )
        if prior is not None:
            if prior["request_digest"] != request_digest:
                raise _error(
                    "shadow.repository.idempotency-mismatch",
                    "Checkpoint idempotency key was reused with a different request digest.",
                )
            checkpoint_result = next(
                (item for item in prior["result"].operation_results if item.record_id.startswith("checkpoint-")),
                None,
            )
            if checkpoint_result and checkpoint_result.resulting_version:
                return {
                    "checkpoint": self.repository.get(checkpoint_result.record_id, checkpoint_result.resulting_version),
                    "task": self.get_task(task_id, principal_ref, space_id),
                    "replayed": True,
                }
        task = self._load_task(
            task_id,
            owner_ref=principal_ref,
            space_id=space_id,
            expected_version=expected_task_version,
            require_active=True,
        )
        checkpoint_id = f"checkpoint-{sha256_digest({'task': task_id, 'digest': checkpoint_digest, 'key': idempotency_key})[7:39]}"
        checkpoint_payload = {
            "task_ref": {"record_id": task_id, "version": expected_task_version},
            "checkpoint_kind": checkpoint_kind,
            "checkpoint_digest": checkpoint_digest,
            "runtime_target_kind": runtime_target_kind,
            "runtime_capabilities": runtime_capabilities,
            "native_resume": native_resume,
            "artifact_refs": artifact_refs,
            "created_at": utc_timestamp(),
        }
        task_payload = deepcopy(task["typed_payload"])
        task_payload["checkpoint_refs"] = [*task_payload.get("checkpoint_refs", []), {"record_id": checkpoint_id, "version": 1}]
        task_payload["last_checkpoint_ref"] = {"record_id": checkpoint_id, "version": 1}
        checkpoint_operation = CommitOperation(
            operation_id=f"operation-{checkpoint_id}-create",
            operation="create",
            record_id=checkpoint_id,
            record_type=CHECKPOINT_RECORD_TYPE,
            target_schema_ref=CHECKPOINT_SCHEMA,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            data_classification="personal",
            provenance=Provenance(origin_type="shadow.origin.continuity", origin_ref=task_id),
            retention_policy_ref=RETENTION_REF,
            typed_payload=checkpoint_payload,
        )
        task_operation = self._task_operation(
            operation_id=f"operation-{task_id}-checkpoint",
            operation="update",
            task_id=task_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=task_payload,
            expected_version=expected_task_version,
            origin_ref=checkpoint_id,
        )
        result = self._commit(
            [checkpoint_operation, task_operation], principal_ref, space_id, idempotency_key,
            request_digest, f"commit-request-{checkpoint_id}", principal_ref,
        )
        checkpoint = self._record_from_result(result, checkpoint_id)
        return {"checkpoint": checkpoint, "task": self.get_task(task_id, principal_ref, space_id), "replayed": result.outcome == "idempotent_replay"}

    def link_run(
        self,
        *,
        task_id: str,
        expected_version: int,
        run_ref: dict[str, Any],
        principal_ref: str,
        space_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        prior = self.repository.idempotency_result(
            f"task:{principal_ref}:{space_id}", idempotency_key
        )
        if prior is not None:
            expected_digest = sha256_digest(
                {"task": task_id, "run": run_ref, "version": expected_version}
            )
            if prior["request_digest"] != expected_digest:
                raise _error(
                    "shadow.repository.idempotency-mismatch",
                    "Run-link idempotency key was reused with a different request digest.",
                )
            return self.get_task(task_id, principal_ref, space_id) or {}
        task = self._load_task(task_id, owner_ref=principal_ref, space_id=space_id, expected_version=expected_version, require_active=False)
        payload = deepcopy(task["typed_payload"])
        if run_ref not in payload.get("run_refs", []):
            payload.setdefault("run_refs", []).append(run_ref)
        operation = self._task_operation(
            operation_id=f"operation-{task_id}-run-link",
            operation="update",
            task_id=task_id,
            owner_ref=principal_ref,
            space_id=space_id,
            created_by=principal_ref,
            typed_payload=payload,
            expected_version=expected_version,
            origin_ref=run_ref["record_id"],
        )
        result = self._commit(
            [operation], principal_ref, space_id, idempotency_key,
            sha256_digest({"task": task_id, "run": run_ref, "version": expected_version}),
            f"commit-request-{task_id}-run-link", principal_ref,
        )
        return self._record_from_result(result, task_id)

    def list_tasks(self, *, owner_ref: str, space_id: str, limit: int = 50) -> list[dict[str, Any]]:
        records = self.repository.query(
            owner_refs={owner_ref}, space_ids={space_id}, record_types={TASK_RECORD_TYPE},
            record_states={"active", "logically_deleted", "erased"}, limit=1_000_000,
        )
        heads: dict[str, dict[str, Any]] = {}
        for record in records:
            if record["record_id"] not in heads or record["version"] > heads[record["record_id"]]["version"]:
                heads[record["record_id"]] = record
        return sorted(heads.values(), key=lambda item: item["record_id"])[:limit]

    def get_task(self, task_id: str, principal_ref: str | None = None, space_id: str | None = None) -> dict[str, Any] | None:
        record = self.repository.get(task_id)
        if record is None or record["record_type"] != TASK_RECORD_TYPE:
            return None
        if principal_ref is not None and space_id is not None:
            self._assert_boundary(record, principal_ref, space_id)
        return record

    def _next_payload(self, current: dict[str, Any] | None, proposal: dict[str, Any]) -> dict[str, Any]:
        operation = proposal["proposed_operation"]
        if current is None:
            return {
                "task_key": proposal["task_key"],
                "goal": proposal["goal"],
                "completion_criteria": proposal["completion_criteria"],
                "lifecycle": "active",
                "run_refs": [], "checkpoint_refs": [], "artifact_refs": [], "trigger_refs": [],
                **({"waiting_condition": proposal["waiting_condition"]} if "waiting_condition" in proposal else {}),
                **({"deadline": proposal["deadline"]} if "deadline" in proposal else {}),
            }
        payload = deepcopy(current["typed_payload"])
        lifecycle = payload["lifecycle"]
        transitions = {
            "activate": {"proposed", "waiting", "paused"},
            "wait": {"active", "paused"},
            "pause": {"active", "waiting"},
            "resume": {"waiting", "paused"},
            "completion_pending": {"active", "waiting", "paused"},
            "complete": {"completion_pending"},
            "fail": {"active", "waiting", "paused", "completion_pending"},
            "cancel": {"active", "waiting", "paused", "completion_pending"},
        }
        if operation not in transitions or lifecycle not in transitions[operation]:
            raise _error(
                "shadow.task.invalid-transition",
                f"Cannot apply {operation} from {lifecycle}.",
                category="conflict",
            )
        lifecycle_map = {
            "activate": "active", "wait": "waiting", "pause": "paused", "resume": "active",
            "completion_pending": "completion_pending", "complete": "completed",
            "fail": "failed", "cancel": "cancelled",
        }
        payload["lifecycle"] = lifecycle_map[operation]
        for key in ("waiting_condition", "deadline", "completion_criteria", "goal"):
            if key in proposal:
                payload[key] = proposal[key]
        if "result_ref" in proposal:
            payload["completion_ref"] = proposal["result_ref"]
        if "failure_summary" in proposal:
            payload["failure_summary"] = proposal["failure_summary"]
        return payload

    def _load_task(self, task_id: str, *, owner_ref: str, space_id: str, expected_version: int | None, require_active: bool) -> dict[str, Any]:
        head = self.repository.get(task_id)
        record = self.repository.get(task_id, expected_version) if expected_version else head
        if head is None or record is None or head["record_type"] != TASK_RECORD_TYPE:
            raise _error("shadow.task.not-found", "Task was not found.")
        self._assert_boundary(head, owner_ref, space_id)
        if expected_version is not None and head["version"] != expected_version:
            raise _error("shadow.repository.expected-version-conflict", "Task expected version conflicts with current head.", category="conflict")
        if require_active and head["record_state"] != "active":
            raise _error("shadow.task.invalid-transition", "Task head is not active.", category="conflict")
        return record

    @staticmethod
    def _task_id(owner_ref: str, space_id: str, task_key: str) -> str:
        return f"task-{sha256_digest({'owner': owner_ref, 'space': space_id, 'task_key': task_key})[7:39]}"

    @staticmethod
    def _assert_boundary(record: dict[str, Any], principal_ref: str, space_id: str) -> None:
        if record["owner_ref"] != principal_ref or record["space_id"] != space_id:
            raise _error("shadow.task.owner-space-mismatch", "Task owner or space does not match the request.", category="unauthorized")

    def _validate(self, payload: dict[str, Any], schema: str) -> None:
        try:
            self.registry.validate(payload, schema)
        except JsonSchemaValidationError as exc:
            raise _error("shadow.task.invalid-transition", "Continuity payload violates its contract.", {"path": list(exc.absolute_path), "detail": exc.message}) from exc

    def _proposal_operation(self, *, operation_id: str, operation: str, proposal_id: str, owner_ref: str, space_id: str, created_by: str, typed_payload: dict[str, Any], expected_version: int | None = None) -> CommitOperation:
        self._validate(typed_payload, TASK_PROPOSAL_RECORD_SCHEMA)
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=proposal_id, record_type=PROPOSAL_RECORD_TYPE, target_schema_ref=TASK_PROPOSAL_RECORD_SCHEMA, owner_ref=owner_ref, space_id=space_id, created_by=created_by, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.task-proposal", origin_ref=proposal_id), retention_policy_ref=RETENTION_REF, typed_payload=typed_payload, expected_version=expected_version)

    def _task_operation(self, *, operation_id: str, operation: str, task_id: str, owner_ref: str, space_id: str, created_by: str, typed_payload: dict[str, Any], expected_version: int | None, origin_ref: str) -> CommitOperation:
        self._validate(typed_payload, TASK_SCHEMA)
        return CommitOperation(operation_id=operation_id, operation=operation, record_id=task_id, record_type=TASK_RECORD_TYPE, target_schema_ref=TASK_SCHEMA, owner_ref=owner_ref, space_id=space_id, created_by=created_by, data_classification="personal", provenance=Provenance(origin_type="shadow.origin.continuity", origin_ref=origin_ref), retention_policy_ref=RETENTION_REF, typed_payload=typed_payload, expected_version=expected_version)

    def _commit(self, operations: list[CommitOperation], owner_ref: str, space_id: str, idempotency_key: str, request_digest: str, commit_request_id: str, actor_ref: str) -> Any:
        result = self.authority.commit(CommitPlan(commit_request_id=commit_request_id, idempotency_scope=f"task:{owner_ref}:{space_id}", idempotency_key=idempotency_key, request_digest=request_digest, actor_ref=actor_ref, operations=operations, prepared_at=utc_timestamp()))
        if result.outcome == "conflict":
            raise _error("shadow.repository.expected-version-conflict", "Task expected version conflicts with current head.", category="conflict")
        if result.outcome == "failed":
            details = result.structured_error or {}
            raise _error(details.get("code", "shadow.task.commit-failed"), details.get("message", "Task commit failed."), details, category=details.get("category", "validation"))
        return result

    def _record_from_result(self, result: Any, record_id: str) -> dict[str, Any]:
        operation_result = next(item for item in result.operation_results if item.record_id == record_id)
        record = self.repository.get(record_id, operation_result.resulting_version)
        if record is None:
            raise _error("shadow.repository.record-missing", "Continuity record could not be read back.")
        return record

    def _require_available(self) -> None:
        if not self.repository.available:
            raise _error("shadow.repository.unavailable", "Canonical Repository is unavailable; Task was not committed.", category="unavailable")


def _error(code: str, message: str, details: dict[str, Any] | None = None, *, category: str = "validation") -> ShadowDomainError:
    return ShadowDomainError(ShadowError(code=code, category=category, message=message, typed_details=details))


def _invalid(message: str) -> ShadowDomainError:
    return _error("shadow.task.invalid-transition", message)
