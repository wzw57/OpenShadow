# Phase 0 migration baseline

The reference store uses SQLAlchemy metadata for the first local bootstrap and
SQLite WAL for durable writes. Alembic owns all subsequent physical schema
migrations; application code must not issue ad-hoc production `ALTER TABLE`
statements.

The first migration must preserve the logical contracts in
`docs/contract-baseline.md`: canonical records are immutable by version,
expected-version writes are compare-and-swap, and idempotency records are
digest-bound. PostgreSQL compatibility is a later Store Profile and is not
required for the Phase 0 local loop.
