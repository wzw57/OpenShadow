from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, event, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .errors import RepositoryUnavailable, ShadowError
from .ids import new_id, sha256_digest, utc_timestamp
from .models import CanonicalEnvelope, CommitBatchResult, CommitPlan, OperationResult


class Base(DeclarativeBase):
    pass


class RecordVersionRow(Base):
    __tablename__ = "canonical_records"

    record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_type: Mapped[str] = mapped_column(String(200), index=True)
    record_state: Mapped[str] = mapped_column(String(32), index=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    envelope_json: Mapped[str] = mapped_column(Text)


class IdempotencyRow(Base):
    __tablename__ = "repository_idempotency"

    idempotency_scope: Mapped[str] = mapped_column(String(500), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(71))
    outcome: Mapped[str] = mapped_column(String(32))
    result_digest: Mapped[str] = mapped_column(String(71))
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRow(Base):
    __tablename__ = "run_events"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True)
    event_type: Mapped[str] = mapped_column(String(200))
    payload_json: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CanonicalRepository:
    """SQLite-backed Canonical Repository with atomic CAS commit batches."""

    def __init__(self, database_url: str | Path = "sqlite:///shadow.db") -> None:
        if isinstance(database_url, Path):
            database_url = f"sqlite:///{database_url.resolve().as_posix()}"
        engine_kwargs: dict[str, Any] = {"future": True}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        self.engine = create_engine(database_url, **engine_kwargs)
        if self.engine.url.get_backend_name() == "sqlite":

            @event.listens_for(self.engine, "connect")
            def _sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False, future=True)
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available

    def health(self) -> dict[str, Any]:
        if not self._available:
            return {"status": "unavailable", "durable": False}
        with self._session_factory() as session:
            session.execute(select(func.count()).select_from(RecordVersionRow)).scalar_one()
        return {"status": "healthy", "durable": True}

    def current_version(self, record_id: str, session: Session | None = None) -> int | None:
        owns_session = session is None
        session = session or self._session_factory()
        try:
            return session.scalar(
                select(func.max(RecordVersionRow.version)).where(
                    RecordVersionRow.record_id == record_id
                )
            )
        finally:
            if owns_session:
                session.close()

    def get(
        self, record_id: str, version: int | None = None, include_states: set[str] | None = None
    ) -> dict[str, Any] | None:
        if not self._available:
            raise RepositoryUnavailable()
        include_states = include_states or {"active", "logically_deleted", "erased"}
        with self._session_factory() as session:
            query = select(RecordVersionRow).where(
                RecordVersionRow.record_id == record_id,
                RecordVersionRow.record_state.in_(include_states),
            )
            if version is not None:
                query = query.where(RecordVersionRow.version == version)
            else:
                query = query.order_by(RecordVersionRow.version.desc()).limit(1)
            row = session.scalar(query)
            return json.loads(row.envelope_json) if row else None

    def query(
        self,
        *,
        owner_refs: set[str] | None = None,
        space_ids: set[str] | None = None,
        record_types: set[str] | None = None,
        record_states: set[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self._available:
            raise RepositoryUnavailable()
        with self._session_factory() as session:
            query = select(RecordVersionRow).where(
                RecordVersionRow.record_state.in_(record_states or {"active"})
            )
            if record_types:
                query = query.where(RecordVersionRow.record_type.in_(record_types))
            query = query.order_by(RecordVersionRow.committed_at, RecordVersionRow.record_id).limit(
                limit
            )
            rows = session.scalars(query).all()
            records = [json.loads(row.envelope_json) for row in rows]
        if owner_refs:
            records = [record for record in records if record["owner_ref"] in owner_refs]
        if space_ids:
            records = [record for record in records if record["space_id"] in space_ids]
        return records[:limit]

    def commit_batch(self, plan: CommitPlan) -> CommitBatchResult:
        if not self._available:
            raise RepositoryUnavailable()
        with self._session_factory.begin() as session:
            prior = session.get(IdempotencyRow, (plan.idempotency_scope, plan.idempotency_key))
            if prior:
                if prior.request_digest != plan.request_digest:
                    return CommitBatchResult(
                        outcome="failed",
                        operation_results=[],
                        structured_error=ShadowError(
                            code="shadow.repository.idempotency-mismatch",
                            category="validation",
                            message="Idempotency key was reused with a different request digest.",
                        ).as_dict(),
                    )
                prior_result = CommitBatchResult.model_validate(json.loads(prior.result_json))
                replay_outcome = (
                    "idempotent_replay" if prior.outcome == "committed" else prior.outcome
                )
                return prior_result.model_copy(update={"outcome": replay_outcome})

            record_ids = [operation.record_id for operation in plan.operations]
            if len(record_ids) != len(set(record_ids)):
                return self._failed_result(
                    "shadow.repository.duplicate-operation",
                    "A batch cannot mutate a record more than once.",
                )

            results: list[OperationResult] = []
            existing: dict[str, int | None] = {}
            rows_to_add: list[RecordVersionRow] = []
            for operation in plan.operations:
                current = self.current_version(operation.record_id, session)
                existing[operation.record_id] = current
                if operation.operation == "create":
                    if current is not None:
                        results.append(
                            OperationResult(
                                operation_id=operation.operation_id,
                                record_id=operation.record_id,
                                conflict_current_version=current,
                            )
                        )
                        continue
                    next_version = 1
                    previous_version = None
                else:
                    if current is None or operation.expected_version != current:
                        results.append(
                            OperationResult(
                                operation_id=operation.operation_id,
                                record_id=operation.record_id,
                                conflict_current_version=current,
                            )
                        )
                        continue
                    next_version = current + 1
                    previous_version = current
                committed_at = utc_timestamp()
                envelope = CanonicalEnvelope(
                    record_id=operation.record_id,
                    record_type=operation.record_type,
                    schema_ref=operation.target_schema_ref,
                    owner_ref=operation.owner_ref,
                    space_id=operation.space_id,
                    created_by=operation.created_by,
                    data_classification=operation.data_classification,
                    provenance=operation.provenance,
                    version=next_version,
                    retention_policy_ref=operation.retention_policy_ref,
                    record_state=operation.record_state,
                    created_at=committed_at
                    if previous_version is None
                    else self._created_at(operation.record_id, session),
                    committed_at=committed_at,
                    typed_payload=operation.typed_payload,
                ).model_dump(mode="json", exclude_none=True)
                rows_to_add.append(
                    RecordVersionRow(
                        record_id=operation.record_id,
                        version=next_version,
                        record_type=operation.record_type,
                        record_state=operation.record_state,
                        committed_at=datetime.fromisoformat(committed_at.replace("Z", "+00:00")),
                        envelope_json=json.dumps(envelope, ensure_ascii=False, sort_keys=True),
                    )
                )
                results.append(
                    OperationResult(
                        operation_id=operation.operation_id,
                        record_id=operation.record_id,
                        previous_version=previous_version,
                        resulting_version=next_version,
                    )
                )

            conflict = next(
                (result for result in results if result.conflict_current_version is not None), None
            )
            if conflict:
                result = CommitBatchResult(outcome="conflict", operation_results=results)
                self._save_idempotency(session, plan, result)
                return result

            session.add_all(rows_to_add)
            result = CommitBatchResult(
                outcome="committed",
                commit_id=new_id("commit"),
                repository_revision=new_id("revision"),
                committed_at=utc_timestamp(),
                operation_results=results,
            )
            self._save_idempotency(session, plan, result)
            return result

    def _created_at(self, record_id: str, session: Session) -> str:
        row = session.scalar(
            select(RecordVersionRow).where(
                RecordVersionRow.record_id == record_id,
                RecordVersionRow.version == 1,
            )
        )
        if not row:
            return utc_timestamp()
        return json.loads(row.envelope_json)["created_at"]

    def _save_idempotency(
        self, session: Session, plan: CommitPlan, result: CommitBatchResult
    ) -> None:
        result_json = json.dumps(result.model_dump(mode="json", exclude_none=True), sort_keys=True)
        session.add(
            IdempotencyRow(
                idempotency_scope=plan.idempotency_scope,
                idempotency_key=plan.idempotency_key,
                request_digest=plan.request_digest,
                outcome=result.outcome,
                result_digest=sha256_digest(result.model_dump(mode="json", exclude_none=True)),
                result_json=result_json,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _failed_result(code: str, message: str) -> CommitBatchResult:
        return CommitBatchResult(
            outcome="failed",
            operation_results=[],
            structured_error=ShadowError(
                code=code, category="validation", message=message
            ).as_dict(),
        )

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._available:
            raise RepositoryUnavailable()
        with self._session_factory.begin() as session:
            current = (
                session.scalar(select(func.max(EventRow.sequence)).where(EventRow.run_id == run_id))
                or 0
            )
            sequence = current + 1
            event_id = new_id("event")
            occurred_at = utc_timestamp()
            session.add(
                EventRow(
                    run_id=run_id,
                    sequence=sequence,
                    event_id=event_id,
                    event_type=event_type,
                    payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")),
                )
            )
        return {
            "event_id": event_id,
            "run_id": run_id,
            "sequence": sequence,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "typed_payload": payload,
        }

    def events(self, run_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        if not self._available:
            raise RepositoryUnavailable()
        with self._session_factory() as session:
            rows = session.scalars(
                select(EventRow)
                .where(
                    EventRow.run_id == run_id,
                    EventRow.sequence > after_sequence,
                )
                .order_by(EventRow.sequence)
            ).all()
        return [
            {
                "event_id": row.event_id,
                "run_id": run_id,
                "sequence": row.sequence,
                "event_type": row.event_type,
                "occurred_at": row.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "typed_payload": json.loads(row.payload_json),
            }
            for row in rows
        ]
