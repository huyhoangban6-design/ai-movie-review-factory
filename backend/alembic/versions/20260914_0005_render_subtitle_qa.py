"""video_renders, subtitles, qa_reports

Revision ID: 20260914_0005
Revises: 20260914_0004
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0005"
down_revision: Union[str, None] = "20260914_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)


def upgrade() -> None:
    # projects: idempotency trước đây dựa vào Job (đã bỏ khi Phase 2 không kickoff job) — lưu trên chính project.
    op.add_column("projects", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_projects_idempotency_key"), "projects", ["idempotency_key"], unique=True)

    # jobs: movie có thể chưa nằm trong project nào → project_id nullable.
    # batch_alter_table để hỗ trợ SQLite (không có ALTER COLUMN native).
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.Integer(), nullable=True)

    # video_renders: FFmpeg render output (Phase 5)
    op.create_table(
        "video_renders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(length=20), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("video_codec", sa.String(length=20), nullable=True),
        sa.Column("audio_codec", sa.String(length=20), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("render_config", sa.JSON(), nullable=True),
        sa.Column("render_log", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
    op.create_index(op.f("ix_video_renders_script_id"), "video_renders", ["script_id"], unique=False)
    op.create_index(op.f("ix_video_renders_owner_id"), "video_renders", ["owner_id"], unique=False)

    # subtitles: caption file per script (SRT/VTT)
    op.create_table(
        "subtitles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("cue_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["generation_id"], ["voice_generations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subtitles_script_id"), "subtitles", ["script_id"], unique=False)
    op.create_index(op.f("ix_subtitles_owner_id"), "subtitles", ["owner_id"], unique=False)
    op.create_index(op.f("ix_subtitles_generation_id"), "subtitles", ["generation_id"], unique=False)

    # qa_reports: gate checks for the final QA gate (docs/12)
    op.create_table(
        "qa_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("gate", sa.String(length=20), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(op.f("ix_qa_reports_script_id"), "qa_reports", ["script_id"], unique=False)
    op.create_index(op.f("ix_qa_reports_owner_id"), "qa_reports", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_qa_reports_owner_id"), table_name="qa_reports")
    op.drop_index(op.f("ix_qa_reports_script_id"), table_name="qa_reports")
    op.drop_table("qa_reports")
    op.drop_index(op.f("ix_subtitles_generation_id"), table_name="subtitles")
    op.drop_index(op.f("ix_subtitles_owner_id"), table_name="subtitles")
    op.drop_index(op.f("ix_subtitles_script_id"), table_name="subtitles")
    op.drop_table("subtitles")
    op.drop_index(op.f("ix_video_renders_owner_id"), table_name="video_renders")
    op.drop_index(op.f("ix_video_renders_script_id"), table_name="video_renders")
    op.drop_table("video_renders")
    op.drop_index(op.f("ix_projects_idempotency_key"), table_name="projects")
    op.drop_column("projects", "idempotency_key")
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.Integer(), nullable=False)