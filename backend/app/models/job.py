import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseORM


class JobType(str, enum.Enum):
    MOVIE_DISCOVERY = "movie_discovery"
    MOVIE_RESEARCH = "movie_research"
    OPPORTUNITY_SCORE = "opportunity_score"
    CONTENT_ANGLE = "content_angle"
    SCRIPT = "script"
    VOICE = "voice"
    TIMELINE = "timeline"
    ASSETS = "assets"
    COPYRIGHT = "copyright"
    RENDER = "render"
    SUBTITLE = "subtitle"
    QA = "qa"
    UPLOAD = "upload"
    PUBLISH = "publish"
    # ---------- Phase 7: analytics / experiments / learning ----------
    ANALYTICS = "analytics"
    COMPETITOR_RESEARCH = "competitor_research"
    LEARN = "learn"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseORM):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_type: Mapped[JobType] = mapped_column(SAEnum(JobType, native_enum=False, length=32), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus, native_enum=False, length=16), default=JobStatus.PENDING, nullable=False)
    input_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")  # pyright: ignore