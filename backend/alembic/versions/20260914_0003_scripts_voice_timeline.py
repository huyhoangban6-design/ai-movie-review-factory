"""scripts, script segments, voice profiles/providers, generations, timeline

Revision ID: 20260914_0003
Revises: 20260914_0002
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0003"
down_revision: Union[str, None] = "20260914_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> sa.Column:
    return sa.Column(sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "scripts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("angle_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_s", sa.Float(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["angle_id"], ["content_angles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scripts_movie_id"), "scripts", ["movie_id"], unique=False)
    op.create_index(op.f("ix_scripts_angle_id"), "scripts", ["angle_id"], unique=False)

    op.create_table(
        "script_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("duration_estimate_s", sa.Float(), nullable=True),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_script_segments_script_id"), "script_segments", ["script_id"], unique=False)

    op.create_table(
        "voice_providers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("tier", sa.String(length=24), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("default_voice_id", sa.String(length=120), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("style", sa.String(length=120), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("emotion", sa.String(length=60), nullable=True),
        sa.Column("commercial_use", sa.String(length=16), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("cloning_permission", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("quality_rank", sa.Integer(), nullable=False),
        sa.Column("cost_per_1k_chars", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "voice_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("voice_id", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("style", sa.String(length=120), nullable=True),
        sa.Column("speed", sa.Float(), nullable=False),
        sa.Column("emotion", sa.String(length=60), nullable=True),
        sa.Column("commercial_use", sa.String(length=16), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("cloning_permission", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
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
    op.create_index(op.f("ix_voice_profiles_owner_id"), "voice_profiles", ["owner_id"], unique=False)

    op.create_table(
        "voice_generations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("voice_profile_id", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("audio_duration_s", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("voice_id", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False),
        sa.Column("words", sa.JSON(), nullable=True),
        sa.Column("sentences", sa.JSON(), nullable=True),
        sa.Column("license_info", sa.JSON(), nullable=True),
        sa.Column("cost", sa.Numeric(precision=10, scale=4), nullable=True),
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
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_voice_generations_script_id"), "voice_generations", ["script_id"], unique=False)
    op.create_index(op.f("ix_voice_generations_owner_id"), "voice_generations", ["owner_id"], unique=False)
    op.create_index(op.f("ix_voice_generations_text_hash"), "voice_generations", ["text_hash"], unique=False)
    op.create_index(
        op.f("ix_voice_generations_voice_profile_id"), "voice_generations", ["voice_profile_id"], unique=False
    )

    op.create_table(
        "script_timelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("total_duration_s", sa.Float(), nullable=True),
        sa.Column("segments", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        _now(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["generation_id"], ["voice_generations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_script_timelines_script_id"), "script_timelines", ["script_id"], unique=False)
    op.create_index(
        op.f("ix_script_timelines_generation_id"), "script_timelines", ["generation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_script_timelines_generation_id"), table_name="script_timelines")
    op.drop_index(op.f("ix_script_timelines_script_id"), table_name="script_timelines")
    op.drop_table("script_timelines")
    op.drop_index(op.f("ix_voice_generations_voice_profile_id"), table_name="voice_generations")
    op.drop_index(op.f("ix_voice_generations_text_hash"), table_name="voice_generations")
    op.drop_index(op.f("ix_voice_generations_owner_id"), table_name="voice_generations")
    op.drop_index(op.f("ix_voice_generations_script_id"), table_name="voice_generations")
    op.drop_table("voice_generations")
    op.drop_index(op.f("ix_voice_profiles_owner_id"), table_name="voice_profiles")
    op.drop_table("voice_profiles")
    op.drop_table("voice_providers")
    op.drop_index(op.f("ix_script_segments_script_id"), table_name="script_segments")
    op.drop_table("script_segments")
    op.drop_index(op.f("ix_scripts_angle_id"), table_name="scripts")
    op.drop_index(op.f("ix_scripts_movie_id"), table_name="scripts")
    op.drop_table("scripts")