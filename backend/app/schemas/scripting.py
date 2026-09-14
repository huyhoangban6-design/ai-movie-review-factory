import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research import Angle


# ---------- script section structure (docs/05: Script Agent) ----------
class SectionId(str, enum.Enum):
    HOOK = "hook"
    THESIS = "thesis"
    CONTEXT = "context"
    ANALYSIS = "analysis"
    EVIDENCE = "evidence"
    CHARACTER_THEME = "character_theme"
    CRITIQUE = "critique"
    CONCLUSION = "conclusion"
    CTA = "cta"


SECTION_TITLES: dict[str, str] = {
    SectionId.HOOK.value: "Hook (mở hấp dẫn)",
    SectionId.THESIS.value: "Luận điểm chính",
    SectionId.CONTEXT.value: "Bối cảnh phim",
    SectionId.ANALYSIS.value: "Phân tích",
    SectionId.EVIDENCE.value: "Bằng chứng / ví dụ",
    SectionId.CHARACTER_THEME.value: "Nhân vật & chủ đề",
    SectionId.CRITIQUE.value: "Phê bình",
    SectionId.CONCLUSION.value: "Kết luận",
    SectionId.CTA.value: "Kêu gọi hành động",
}


# ---------- internal DTOs (providers <-> services) ----------
class ScriptSegment(BaseModel):
    section: SectionId
    text: str = Field(min_length=8)


class ScriptOutput(BaseModel):
    title: str
    segments: list[ScriptSegment] = Field(default_factory=list)
    word_count: int = 0
    estimated_duration_s: float = 0.0


class WordTimestamp(BaseModel):
    word: str
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)


class SentenceTimestamp(BaseModel):
    sentence: str
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)


class LicenseInfo(BaseModel):
    commercial_use: str = "unknown"
    license_url: Optional[str] = None
    cloning_permission: bool = False


class VoiceOutput(BaseModel):
    provider: str
    model: str
    voice_id: str
    language: str = "vi"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    audio_url: Optional[str] = None
    duration_s: float = Field(ge=0)
    words: list[WordTimestamp] = Field(default_factory=list)
    sentences: list[SentenceTimestamp] = Field(default_factory=list)
    license: LicenseInfo = Field(default_factory=LicenseInfo)


class TimelineSegment(BaseModel):
    segment_id: Optional[int] = None
    position: int
    section: str
    text: str
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)


class TimelineOutput(BaseModel):
    total_duration_s: float = Field(ge=0)
    segments: list[TimelineSegment] = Field(default_factory=list)
    matches: bool = True


# ---------- response DTOs cho GET (detail view) ----------
class ScriptSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    angle_id: Optional[int] = None
    version: int
    status: str
    title: str
    word_count: int
    estimated_duration_s: Optional[float] = None
    created_at: datetime


class SegmentDetailOut(BaseModel):
    id: int
    position: int
    section: str
    text: str
    duration_estimate_s: Optional[float] = None


class GenerationOut(BaseModel):
    id: int
    status: str
    provider: str
    model: str
    voice_id: str
    language: str
    speed: float
    audio_url: Optional[str] = None
    audio_duration_s: Optional[float] = None
    license_info: Optional[dict] = None
    cost: Optional[float] = None
    created_at: datetime


class TimelineOut(BaseModel):
    id: int
    generation_id: Optional[int] = None
    total_duration_s: Optional[float] = None
    segments: Optional[list] = None
    created_at: datetime


class ScriptDetailOut(BaseModel):
    id: int
    movie_id: int
    angle_id: Optional[int] = None
    version: int
    status: str
    title: str
    word_count: int
    estimated_duration_s: Optional[float] = None
    created_at: datetime
    segments: list[SegmentDetailOut] = Field(default_factory=list)
    latest_generation: Optional[GenerationOut] = None
    timeline: Optional[TimelineOut] = None