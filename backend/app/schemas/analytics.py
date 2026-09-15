from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Phase 7: analytics (docs/13) ----------
# DTO internal giữa provider <-> services; response schema ở cuối file.
class VideoMetricsOutput(BaseModel):
    """Bộ metric một video (CTR, views, watch time, retention, revenue, traffic…)."""

    video_id: str
    captured_at: datetime | None = None
    views: int = 0
    impressions: int = 0
    clicks: int = 0
    ctr_pct: float = 0.0
    likes: int = 0
    comments: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration_s: float = 0.0
    retention_avg_pct: float = 0.0
    retention_curve: list[float] = Field(default_factory=list)
    traffic_sources: dict = Field(default_factory=dict)
    subscribers_gained: int = 0
    revenue_usd: float = 0.0
    rpm_usd: float = 0.0
    imported_from: str = "offline"
    simulated: bool = True
    metadata: dict = Field(default_factory=dict)


class CompetitorVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_title: Optional[str] = None
    score: Optional[int] = None
    influence: Optional[int] = None
    view_count: Optional[int] = None
    retrieval_url: Optional[str] = None


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    genre: Optional[str] = None
    influence: Optional[int] = None
    top_videos: Optional[list] = None
    videos: list[CompetitorVideoOut] = Field(default_factory=list)


class CompetitorsOutput(BaseModel):
    movie_id: int
    competitors: list[CompetitorOut] = Field(default_factory=list)


class InsightOutput(BaseModel):
    scope: str = "global"
    movie_id: Optional[int] = None
    publication_id: Optional[int] = None
    category: str
    insight: str
    suggestion: Optional[str] = None
    signal_value: Optional[float] = None
    strategy_version: Optional[str] = None
    status: str = "open"


class ProposedStrategy(BaseModel):
    strategy_version: str = "v2"
    weights: dict = Field(default_factory=dict)
    rationale: Optional[str] = None


class LearnProviderOutput(BaseModel):
    insights: list[InsightOutput] = Field(default_factory=list)
    proposed_strategy: ProposedStrategy = Field(default_factory=ProposedStrategy)


# ---------- request / response (API) ----------
class AnalyticsRefreshRequest(BaseModel):
    pass


class VideoMetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publication_id: int
    video_id: Optional[str] = None
    captured_at: Optional[datetime] = None
    views: int
    impressions: int
    clicks: int
    ctr_pct: Optional[float] = None
    likes: int
    comments: int
    watch_time_hours: float
    avg_view_duration_s: Optional[float] = None
    retention_avg_pct: Optional[float] = None
    retention_curve: Optional[list] = None
    traffic_sources: Optional[dict] = None
    subscribers_gained: int
    revenue_usd: float
    rpm_usd: Optional[float] = None
    created_at: datetime


class VideoMetricsResult(BaseModel):
    job_id: int
    publication_id: int
    snapshot_id: int
    metrics: VideoMetricsOut


class AnalyticsVideoOut(BaseModel):
    publication_id: int
    video_id: Optional[str] = None
    title: str
    status: str
    metrics: VideoMetricsOut | None = None
    source: str = "stored"  # stored / derived


class AnalyticsHistoryOut(BaseModel):
    publication_id: int
    snapshots: list[VideoMetricsOut] = Field(default_factory=list)


class VideoMetricsInput(BaseModel):
    publication_id: int


class AnalyticsSummaryOut(BaseModel):
    video_count: int = 0
    total_views: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    avg_ctr_pct: float = 0.0
    total_watch_time_hours: float = 0.0
    avg_retention_pct: float = 0.0
    total_likes: int = 0
    total_comments: int = 0
    total_revenue_usd: float = 0.0
    avg_rpm_usd: float = 0.0
    insight_count: int = 0


class CompetitorResearchRequest(BaseModel):
    movie_id: int


class CompetitorResearchResult(BaseModel):
    job_id: int
    movie_id: int
    competitors: list[CompetitorOut] = Field(default_factory=list)


class LearnRequest(BaseModel):
    movie_id: int | None = Field(default=None)
    scope: str = Field(default="global", pattern="^(global|movie)$")


class LearnResult(BaseModel):
    job_id: int
    scope: str
    movie_id: int | None = None
    insight_count: int = 0
    insights: list[InsightOutput] = Field(default_factory=list)
    proposed_strategy: ProposedStrategy = Field(default_factory=ProposedStrategy)


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: Optional[int] = None
    publication_id: Optional[int] = None
    scope: str
    category: str
    insight: str
    suggestion: Optional[str] = None
    signal_value: Optional[float] = None
    strategy_version: Optional[str] = None
    status: str
    created_at: datetime


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    strategy_version: str = Field(default="v1", max_length=40)
    weights: dict = Field(default_factory=dict)


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    strategy_version: str
    weights: Optional[dict] = None
    status: str
    stage: str
    notes: Optional[str] = None
    activated_at: Optional[datetime] = None
    created_at: datetime


class ExperimentActivateResult(BaseModel):
    experiment_id: int
    strategy_version: str
    status: str
    detail: str


class StrategyOut(BaseModel):
    strategy_version: str
    weights: dict = Field(default_factory=dict)
    source: str = "default"  # default / experiment
    experiment_id: Optional[int] = None
    applied_to_scoring: bool = True