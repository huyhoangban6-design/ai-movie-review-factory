import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseORM


class ScriptStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CommercialUse(str, enum.Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class VoiceRouteTier(str, enum.Enum):
    CLOUD = "cloud"
    GPU_CLOUD = "gpu_cloud"
    SELF_HOSTED = "self_hosted"
    BACKUP = "backup"


class Script(BaseORM):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    angle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content_angles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[ScriptStatus] = mapped_column(
        SAEnum(ScriptStatus, native_enum=False, length=24), default=ScriptStatus.DRAFT, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    visual_plan: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pipeline_status: Mapped[str] = mapped_column(String(24), default="script", nullable=False)

    segments: Mapped[list["ScriptSegment"]] = relationship(
        back_populates="script", cascade="all, delete-orphan", order_by="ScriptSegment.position"
    )
    generations: Mapped[list["VoiceGeneration"]] = relationship(
        back_populates="script", cascade="all, delete-orphan", order_by="VoiceGeneration.id"
    )


class ScriptSegment(BaseORM):
    __tablename__ = "script_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(40), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_estimate_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    script: Mapped["Script"] = relationship(back_populates="segments")  # pyright: ignore


class VoiceProvider(BaseORM):
    __tablename__ = "voice_providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[VoiceRouteTier] = mapped_column(
        SAEnum(VoiceRouteTier, native_enum=False, length=24),
        default=VoiceRouteTier.CLOUD,
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    default_voice_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="vi", nullable=False)
    style: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    commercial_use: Mapped[CommercialUse] = mapped_column(
        SAEnum(CommercialUse, native_enum=False, length=16), default=CommercialUse.UNKNOWN, nullable=False
    )
    license_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cloning_permission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    quality_rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_per_1k_chars: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class VoiceProfile(BaseORM):
    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="vi", nullable=False)
    style: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    emotion: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    commercial_use: Mapped[CommercialUse] = mapped_column(
        SAEnum(CommercialUse, native_enum=False, length=16), default=CommercialUse.UNKNOWN, nullable=False
    )
    license_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cloning_permission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class VoiceGeneration(BaseORM):
    __tablename__ = "voice_generations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    voice_profile_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("voice_profiles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="vi", nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    words: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    sentences: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    license_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    script: Mapped["Script"] = relationship(back_populates="generations")  # pyright: ignore


class ScriptTimeline(BaseORM):
    __tablename__ = "script_timelines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    generation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("voice_generations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    total_duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    segments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)