from datetime import datetime

from pydantic import BaseModel

from app.schemas.research import Angle, OpportunityScoreOutput, ResearchedSource


class SourceOut(ResearchedSource):
    id: int


class OpportunityOut(BaseModel):
    id: int
    overall: float | None = None
    sub_scores: dict | None = None
    confidence: float | None = None
    rationale: str | None = None
    created_at: datetime


class MovieOut(BaseModel):
    id: int
    owner_id: int
    project_id: int | None = None
    title: str
    year: int | None = None
    director: str | None = None
    genres: list | None = None
    synopsis: str | None = None
    poster_url: str | None = None
    imdb_id: str | None = None
    tmdb_id: int | None = None
    status: str = "verified"
    created_at: datetime


class MovieDetailOut(MovieOut):
    sources: list[SourceOut] = []
    summaries: list[str] = []
    opportunity: OpportunityOut | None = None
    angles: list[Angle] = []
    facts: list[str] = []