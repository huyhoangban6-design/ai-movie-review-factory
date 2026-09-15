"""cost_records, system_logs + cost/retry columns (Phase 8 cost engine)

Revision ID: 20260915_0008
Revises: 20260914_0007
Create Date: 2026-09-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0008"
down_revision: Union[str, None] = "20260914_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cost_records: estimated + actual cost theo provider/model/job (docs/03, docs/11)
    op.create_table(
        "cost_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("units", sa.Float(), nullable=False),
        sa.Column("unit_rate_usd", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("actual_cost_usd", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_records_owner_id"), "cost_records", ["owner_id"], unique=False)
    op.create_index(op.f("ix_cost_records_project_id"), "cost_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_cost_records_job_id"), "cost_records", ["job_id"], unique=False)
    op.create_index(op.f("ix_cost_records_job_type"), "cost_records", ["job_type"], unique=False)

    # system_logs: structured log truy vấn được (docs/03) — cost alerts, provider failures
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("logger", sa.String(length=64), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_logs_owner_id"), "system_logs", ["owner_id"], unique=False)

    # cost_mode cho project budget (docs/11: free|balanced|premium)
    op.add_column(
        "projects",
        sa.Column("cost_mode", sa.String(length=16), server_default="balanced", nullable=False),
    )

    # job: cost + provider + retry metadata
    op.add_column("jobs", sa.Column("cost_usd", sa.Float(), nullable=True))
    op.add_column("jobs", sa.Column("provider_name", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("max_retries", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # SQLite: batch mode để drop column an toàn.
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("next_retry_at")
        batch.drop_column("max_retries")
        batch.drop_column("provider_name")
        batch.drop_column("cost_usd")

    with op.batch_alter_table("projects") as batch:
        batch.drop_column("cost_mode")

    op.drop_index(op.f("ix_system_logs_owner_id"), table_name="system_logs")
    op.drop_table("system_logs")
    op.drop_index(op.f("ix_cost_records_job_type"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_job_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_project_id"), table_name="cost_records")
    op.drop_index(op.f("ix_cost_records_owner_id"), table_name="cost_records")
    op.drop_table("cost_records")