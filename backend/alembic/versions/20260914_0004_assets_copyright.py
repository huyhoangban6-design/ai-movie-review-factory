"""assets, asset_sources, copyright_reviews, script visual plan

Revision ID: 20260914_0004
Revises: 20260914_0003
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0004"
down_revision: Union[str, None] = "20260914_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)


def upgrade() -> None:
    # Add visual_plan and pipeline_status columns to scripts
    op.add_column("scripts", sa.Column("visual_plan", sa.JSON(), nullable=True))
    op.add_column("scripts", sa.Column("pipeline_status", sa.String(length=24), server_default="script", nullable=False))

    # Create assets table
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=120), nullable=True),
        sa.Column("commercial_use", sa.String(length=16), nullable=True),
        sa.Column("owner_name", sa.String(length=255), nullable=True),
        sa.Column("acquisition_time", sa.Float(), nullable=True),
        sa.Column("usage_context", sa.String(length=80), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("transformations", sa.JSON(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_script_id"), "assets", ["script_id"], unique=False)
    op.create_index(op.f("ix_assets_owner_id"), "assets", ["owner_id"], unique=False)

    # Create asset_sources table
    op.create_table(
        "asset_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_sources_asset_id"), "asset_sources", ["asset_id"], unique=False)

    # Create copyright_reviews table
    op.create_table(
        "copyright_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("duration_warning", sa.Boolean(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("policy_notes", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copyright_reviews_asset_id"), "copyright_reviews", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_copyright_reviews_asset_id"), table_name="copyright_reviews")
    op.drop_table("copyright_reviews")
    op.drop_index(op.f("ix_asset_sources_asset_id"), table_name="asset_sources")
    op.drop_table("asset_sources")
    op.drop_index(op.f("ix_assets_owner_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_script_id"), table_name="assets")
    op.drop_table("assets")
    op.drop_column("scripts", "pipeline_status")
    op.drop_column("scripts", "visual_plan")