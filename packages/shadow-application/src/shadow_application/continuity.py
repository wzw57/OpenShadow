from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from shadow_kernel.admission import AdmissionResult, AdmissionService
from shadow_kernel.errors import ShadowDomainError, ShadowError
from shadow_kernel.ids import sha256_digest
from shadow_kernel.registry import ContractRegistry

CONTINUITY_SCHEMA = "https://schemas.openshadow.dev/contracts/continuity/1.0.0"
TRIGGER_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/TriggerObservation"
INTEGRITY_SCHEMA = f"{CONTINUITY_SCHEMA}#/$defs/IntegrityManifest"


class ClockPort(Protocol):
    def now(self) -> str: ...


class ScheduleAdapter(Protocol):
    def observe(self, *, schedule_key: str, now: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class DeterministicClock:
    current: datetime

    def now(self) -> str:
        return self.current.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def advance(self, seconds: int) -> str:
        self.current += timedelta(seconds=seconds)
        return self.now()


@dataclass(frozen=True, slots=True)
class DeterministicScheduleAdapter:
    trigger_key: str
    condition_met: bool = True

    def observe(self, *, schedule_key: str, now: str) -> dict[str, Any]:
        if schedule_key != self.trigger_key:
            return {
                "trigger_key": schedule_key,
                "observed_at": now,
                "source": "adapter:deterministic-clock",
                "condition_met": False,
                "payload": {},
            }
        return {
            "trigger_key": self.trigger_key,
            "observed_at": now,
            "source": "adapter:deterministic-clock",
            "condition_met": self.condition_met,
            "payload": {"scheduled_for": now},
        }


class StateConditionAdmission:
    """Re-enters the existing Admission path; it never commits State or Task directly."""

    def __init__(self, state_service: Any, admission_service: AdmissionService, registry: ContractRegistry):
        self.state_service = state_service
        self.admission_service = admission_service
        self.registry = registry

    def evaluate_and_admit(
        self,
        *,
        state_id: str,
        expected_state_key: str,
        expected_value: Any,
        principal_ref: str,
        space_id: str,
        request_type: str,
        endpoint_ref: str,
        idempotency_key: str,
    ) -> AdmissionResult | None:
        state = self.state_service.get_state(state_id, principal_ref=principal_ref, space_id=space_id)
        if state is None or state["typed_payload"].get("state_key") != expected_state_key:
            return None
        payload = state["typed_payload"]
        if payload.get("freshness") != "fresh" or payload.get("typed_value") != expected_value:
            return None
        return self.admission_service.admit(
            request_type=request_type,
            input_type="shadow.state-condition",
            work_input={
                "schema_ref": "https://schemas.openshadow.dev/content/state-condition/1.0.0",
                "typed_input": {"state_ref": {"record_id": state_id, "version": state["version"]}},
            },
            principal_ref=principal_ref,
            endpoint_ref=endpoint_ref,
            space_id=space_id,
            idempotency_key=idempotency_key,
        )


def validate_trigger(registry: ContractRegistry, trigger: dict[str, Any]) -> None:
    try:
        registry.validate(trigger, TRIGGER_SCHEMA)
    except Exception as exc:
        raise ShadowDomainError(
            ShadowError(
                code="shadow.schedule.invalid-trigger",
                category="validation",
                message="Schedule adapter returned an invalid trigger observation.",
            )
        ) from exc


class MigrationPort(Protocol):
    def migrate(self, payload: dict[str, Any], *, from_schema: str, to_schema: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class DeterministicMigrationAdapter:
    from_schema: str
    to_schema: str

    def migrate(self, payload: dict[str, Any], *, from_schema: str, to_schema: str) -> dict[str, Any]:
        if from_schema != self.from_schema or to_schema != self.to_schema:
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.migration.incompatible",
                    category="unsupported",
                    message="Migration adapter does not support the requested schema pair.",
                )
            )
        return dict(payload)


class IntegrityService:
    """Digest and ownership verification for portable records; no persistence side effects."""

    def __init__(self, registry: ContractRegistry):
        self.registry = registry

    def build_manifest(self, records: list[dict[str, Any]], *, owner_ref: str, space_id: str) -> dict[str, Any]:
        for record in records:
            if record.get("owner_ref") != owner_ref or record.get("space_id") != space_id:
                raise ShadowDomainError(
                    ShadowError(
                        code="shadow.integrity.owner-space-mismatch",
                        category="unauthorized",
                        message="Integrity manifest crosses an Owner/Space boundary.",
                    )
                )
        entries = [
            {"record_id": record["record_id"], "version": record["version"], "digest": sha256_digest(record)}
            for record in sorted(records, key=lambda item: (item["record_id"], item["version"]))
        ]
        manifest = {
            "manifest_id": f"manifest-{sha256_digest(entries)[7:39]}",
            "schema_version": "1.0.0",
            "owner_ref": owner_ref,
            "space_id": space_id,
            "record_digests": entries,
        }
        manifest["manifest_digest"] = sha256_digest(manifest)
        self.registry.validate(manifest, INTEGRITY_SCHEMA)
        return manifest

    def verify_manifest(self, records: list[dict[str, Any]], manifest: dict[str, Any], *, owner_ref: str, space_id: str) -> bool:
        expected = self.build_manifest(records, owner_ref=owner_ref, space_id=space_id)
        if expected["manifest_digest"] != manifest.get("manifest_digest") or expected["record_digests"] != manifest.get("record_digests"):
            raise ShadowDomainError(
                ShadowError(
                    code="shadow.integrity.digest-mismatch",
                    category="validation",
                    message="Integrity manifest or record digest does not match.",
                )
            )
        return True
