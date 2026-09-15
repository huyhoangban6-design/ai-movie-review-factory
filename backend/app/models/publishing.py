import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseORM


class PublicationStatus(str, enum.Enum):
    PRIVATE_UPLOADED = "private_uploaded"
    READY_TO_PUBLISH = "ready_to_publish"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


class Publication(BaseORM):
    """Package đã upload lên YouTube (docs/13).

    Quy trình Phase 6: upload Private → Human Approval (CP6) → Schedule/Public.
    Không bao giờ tự động public nếu chưa Final QA pass + approval (docs/00 #8).
    """

    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    render_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("video_renders.id", ondelete="SET NULL"), index=True, nullable=True
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[PublicationStatus] = mapped_column(
        SAEnum(PublicationStatus, native_enum=False, length=24),
        default=PublicationStatus.PRIVATE_UPLOADED,
        nullable=False,
    )
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    privacy_status: Mapped[str] = mapped_column(String(16), default="private", nullable=False)
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notify_subscribers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    upload_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Publication id={self.id} script_id={self.script_id} status={self.status.value}>"
