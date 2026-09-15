import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Phase 6: YouTube publishing (docs/13) ----------
class PublishPrivacy(str, enum.Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class UploadRequest(BaseModel):
    script_id: int
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    notify_subscribers: bool = False
    privacy: PublishPrivacy = PublishPrivacy.PRIVATE


class ApproveRequest(BaseModel):
    publication_id: int
    approved: bool = True
    note: str | None = Field(default=None, max_length=5000)


class PublishRequest(BaseModel):
    publication_id: int
    privacy: PublishPrivacy = PublishPrivacy.PUBLIC
    notify_subscribers: bool = False
    publish_at: datetime | None = None


class UploadOutput(BaseModel):
    youtube_video_id: str
    privacy_status: str = "private"
    video_url: str | None = None
    upload_metadata: dict = Field(default_factory=dict)


class PublishOutput(BaseModel):
    youtube_video_id: str
    privacy_status: str = "public"
    status: str = "published"  # published / scheduled
    publish_at: datetime | None = None
    video_url: str | None = None


class PublicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    script_id: int
    render_id: Optional[int] = None
    project_id: Optional[int] = None
    status: str
    youtube_video_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    tags: list = Field(default_factory=list)
    category_id: Optional[str] = None
    privacy_status: str = "private"
    publish_at: Optional[datetime] = None
    published_url: Optional[str] = None
    notify_subscribers: bool = False
    approved: bool = False
    approval_note: Optional[str] = None
    approved_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class UploadResult(BaseModel):
    job_id: int
    publication_id: int
    script_id: int
    upload: UploadOutput


class ApproveResult(BaseModel):
    publication_id: int
    status: str
    approved: bool


class PublishResult(BaseModel):
    job_id: int
    publication_id: int
    script_id: int
    publish: PublishOutput
