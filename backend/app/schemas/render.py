from pydantic import BaseModel, Field


# ---------- Render (FFmpeg) ----------
class RenderRequest(BaseModel):
    script_id: int


class RenderOutput(BaseModel):
    script_id: int
    video_url: str | None = None
    thumbnail_url: str | None = None
    output_path: str | None = None
    resolution: str = Field(default="1280x720")
    fps: int = Field(default=30)
    video_codec: str = "h264"
    audio_codec: str = "aac"
    duration_s: float = Field(ge=0)
    file_size_bytes: int | None = Field(default=None, ge=0)
    render_ok: bool = True


class RenderResult(BaseModel):
    job_id: int
    render_id: int
    script_id: int
    render: RenderOutput


# ---------- Subtitle ----------
class SubtitleRequest(BaseModel):
    script_id: int
    format: str = Field(default="srt", pattern=r"^(srt|vtt)$")


class SubtitleOutput(BaseModel):
    script_id: int
    format: str = "srt"
    language: str = "vi"
    content: str
    duration_s: float = Field(ge=0)
    cue_count: int = Field(ge=0)


class SubtitleResult(BaseModel):
    job_id: int
    subtitle_id: int
    script_id: int
    subtitle: SubtitleOutput


# ---------- QA (docs/12: QA System) ----------
class QACheckItem(BaseModel):
    name: str
    passed: bool
    message: str = ""
    severity: str = "pass"  # pass / warning / fail


class QAReportOutput(BaseModel):
    id: int | None = None
    script_id: int
    gate: str
    passed: bool
    mandatory: bool = False
    checks: list[QACheckItem] = Field(default_factory=list)
    severity: str = "pass"
    notes: str | None = None


class QARequest(BaseModel):
    script_id: int


class QAResult(BaseModel):
    job_id: int
    script_id: int
    reports: list[QAReportOutput] = Field(default_factory=list)
    final_passed: bool = False