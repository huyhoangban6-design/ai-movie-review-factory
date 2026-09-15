"""publications (YouTube private upload → approval → publish)

Revision ID: 20260914_0006
Revises: 20260914_0005
Create Date: 2026-09-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0006"
down_revision: Union[str, None] = "20260914_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)


def upgrade() -> None:
    # publications: package YouTube per script, Phase 6 (docs/13)
    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("render_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("category_id", sa.String(length=32), nullable=True),
        sa.Column("privacy_status", sa.String(length=16), nullable=False),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_url", sa.Text(), nullable=True),
        sa.Column("notify_subscribers", sa.Boolean(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("upload_metadata", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["render_id"], ["video_renders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publications_script_id"), "publications", ["script_id"], unique=False)
    op.create_index(op.f("ix_publications_owner_id"), "publications", ["owner_id"], unique=False)
    op.create_index(op.f("ix_publications_render_id"), "publications", ["render_id"], unique=False)
    op.create_index(op.f("ix_publications_project_id"), "publications", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_publications_project_id"), table_name="publications")
    op.drop_index(op.f("ix_publications_render_id"), table_name="publications")
    op.drop_index(op.f("ix_publications_owner_id"), table_name="publications")
    op.drop_index(op.f("ix_publications_script_id"), table_name="publications")
    op.drop_table("publications")
