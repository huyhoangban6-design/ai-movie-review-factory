from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.job import JobStatus, JobType
from app.schemas.research import Angle, MovieResearchOutput, OpportunityScoreOutput


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    max_cost_per_video: float | None = Field(default=None, gt=0, le=1_000_000)

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    job_type: JobType
    status: JobStatus
    retry_count: int
    input_payload: str | None
    output_summary: str | None
    error_message: str | None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: str
    max_cost_per_video: float | None
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    jobs: list[JobOut] = []


class MessageOut(BaseModel):
    detail: str


# ---------- Phase 2: research / opportunity / angles ----------
class ResearchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    movie_id: int | None = Field(default=None)
    year: int | None = Field(default=None, ge=1880, le=2100)
    genres: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class ResearchResult(ResearchRequest):
    movie_id: int
    output: MovieResearchOutput


class ResearchJob(BaseModel):
    job_id: int
    options: dict = {}


class ScoreRequest(BaseModel):
    movie_id: int


class ScoreResult(BaseModel):
    job_id: int
    opportunity_id: int
    movie_id: int
    score: OpportunityScoreOutput


class AnglesResult(BaseModel):
    job_id: int
    movie_id: int
    angles: list[Angle]