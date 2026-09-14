import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseORM


class RenderStatus(str, enum.Enum):
    RENDERED = "rendered"
    FAILED = "failed"


class QAGate(str, enum.Enum):
    FACT = "fact"
    SCRIPT = "script"
    VOICE = "voice"
    VISUAL = "visual"
    SUBTITLE = "subtitle"
    COPYRIGHT = "copyright"
    TECHNICAL = "technical"
    FINAL = "final"


class QACheckSeverity(str, enum.Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class VideoRender(BaseORM):
    __tablename__ = "video_renders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[RenderStatus] = mapped_column(
        SAEnum(RenderStatus, native_enum=False, length=16),
        default=RenderStatus.RENDERED,
        nullable=False,
    )
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    render_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    render_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<VideoRender id={self.id} script_id={self.script_id} status={self.status.value}>"


class Subtitle(BaseORM):
    __tablename__ = "subtitles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    generation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("voice_generations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    format: Mapped[str] = mapped_column(String(8), default="srt", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="vi", nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Subtitle id={self.id} script_id={self.script_id} format={self.format}>"


class QAReport(BaseORM):
    __tablename__ = "qa_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    gate: Mapped[QAGate] = mapped_column(
        SAEnum(QAGate, native_enum=False, length=20), nullable=False
    )
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    severity: Mapped[QACheckSeverity] = mapped_column(
        SAEnum(QACheckSeverity, native_enum=False, length=16),
        default=QACheckSeverity.PASS,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<QAReport id={self.id} gate={self.gate.value} passed={self.passed}>"