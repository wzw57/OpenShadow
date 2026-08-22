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

The checked-in Alembic baseline is `versions/0001_initial.py`. To initialize or
upgrade a database explicitly:

```powershell
alembic upgrade head
```

Set `SHADOW_DATABASE_URL` to target another SQLite URL. The Repository Port
does not expose Alembic; migration orchestration remains a Store Adapter concern.
