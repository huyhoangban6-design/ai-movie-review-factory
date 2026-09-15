"""youtube_metrics, analytics_insights, experiments, kpi_snapshots (Phase 7)

Revision ID: 20260914_0007
Revises: 20260914_0006
Create Date: 2026-09-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0007"
down_revision: Union[str, None] = "20260914_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)


def upgrade() -> None:
    # youtube_metrics: snapshot analytics 1 video (docs/13 + docs/03)
    op.create_table(
        "youtube_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(length=64), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("ctr_pct", sa.Float(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("watch_time_hours", sa.Float(), nullable=False),
        sa.Column("avg_view_duration_s", sa.Float(), nullable=True),
        sa.Column("retention_avg_pct", sa.Float(), nullable=True),
        sa.Column("retention_curve", sa.JSON(), nullable=True),
        sa.Column("traffic_sources", sa.JSON(), nullable=True),
        sa.Column("subscribers_gained", sa.Integer(), nullable=False),
        sa.Column("revenue_usd", sa.Float(), nullable=False),
        sa.Column("rpm_usd", sa.Float(), nullable=True),
        sa.Column("imported_from", sa.String(length=40), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["publications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_youtube_metrics_publication_id"), "youtube_metrics", ["publication_id"], unique=False)
    op.create_index(op.f("ix_youtube_metrics_owner_id"), "youtube_metrics", ["owner_id"], unique=False)

    # analytics_insights: learning loop output (docs/13)
    op.create_table(
        "analytics_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.Column("publication_id", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("insight", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("signal_value", sa.Float(), nullable=True),
        sa.Column("strategy_version", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["publications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analytics_insights_owner_id"), "analytics_insights", ["owner_id"], unique=False)
    op.create_index(op.f("ix_analytics_insights_movie_id"), "analytics_insights", ["movie_id"], unique=False)
    op.create_index(op.f("ix_analytics_insights_publication_id"), "analytics_insights", ["publication_id"], unique=False)

    # experiments: strategy versions/weights calibration (docs/13 learning loop)
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strategy_version", sa.String(length=40), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_experiments_owner_id"), "experiments", ["owner_id"], unique=False)

    # kpi_snapshots: tổng KPI kênh mỗi lần refresh (docs/03)
    op.create_table(
        "kpi_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_video_count", sa.Integer(), nullable=False),
        sa.Column("total_views", sa.Integer(), nullable=False),
        sa.Column("total_impressions", sa.Integer(), nullable=False),
        sa.Column("total_clicks", sa.Integer(), nullable=False),
        sa.Column("avg_ctr_pct", sa.Float(), nullable=True),
        sa.Column("total_watch_time_hours", sa.Float(), nullable=False),
        sa.Column("avg_retention_pct", sa.Float(), nullable=True),
        sa.Column("total_likes", sa.Integer(), nullable=False),
        sa.Column("total_comments", sa.Integer(), nullable=False),
        sa.Column("total_revenue_usd", sa.Float(), nullable=False),
        sa.Column("avg_rpm_usd", sa.Float(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kpi_snapshots_owner_id"), "kpi_snapshots", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_kpi_snapshots_owner_id"), table_name="kpi_snapshots")
    op.drop_table("kpi_snapshots")
    op.drop_index(op.f("ix_experiments_owner_id"), table_name="experiments")
    op.drop_table("experiments")
    op.drop_index(op.f("ix_analytics_insights_publication_id"), table_name="analytics_insights")
    op.drop_index(op.f("ix_analytics_insights_movie_id"), table_name="analytics_insights")
    op.drop_index(op.f("ix_analytics_insights_owner_id"), table_name="analytics_insights")
    op.drop_table("analytics_insights")
    op.drop_index(op.f("ix_youtube_metrics_owner_id"), table_name="youtube_metrics")
    op.drop_index(op.f("ix_youtube_metrics_publication_id"), table_name="youtube_metrics")
    op.drop_table("youtube_metrics")