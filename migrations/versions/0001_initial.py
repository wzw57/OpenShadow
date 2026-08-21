"""Create the Phase 0-1 SQLite repository tables.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canonical_records",
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=200), nullable=False),
        sa.Column("record_state", sa.String(length=32), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("envelope_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("record_id", "version"),
    )
    op.create_index("ix_canonical_records_record_type", "canonical_records", ["record_type"])
    op.create_index("ix_canonical_records_record_state", "canonical_records", ["record_state"])
    op.create_index("ix_canonical_records_committed_at", "canonical_records", ["committed_at"])
    op.create_table(
        "repository_idempotency",
        sa.Column("idempotency_scope", sa.String(length=500), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_digest", sa.String(length=71), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("result_digest", sa.String(length=71), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_scope", "idempotency_key"),
    )
    op.create_table(
        "run_events",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "sequence"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_run_events_occurred_at", "run_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_run_events_occurred_at", table_name="run_events")
    op.drop_table("run_events")
    op.drop_table("repository_idempotency")
    op.drop_index("ix_canonical_records_committed_at", table_name="canonical_records")
    op.drop_index("ix_canonical_records_record_state", table_name="canonical_records")
    op.drop_index("ix_canonical_records_record_type", table_name="canonical_records")
    op.drop_table("canonical_records")
