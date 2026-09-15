from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseORM


class YouTubeMetric(BaseORM):
    """Snapshot metrics của một video đã xuất bản (docs/13 + docs/03: youtube_metrics).

    Mỗi lần refresh tạo một snapshot mới; GET trả snapshot mới nhất.
    """

    __tablename__ = "youtube_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_view_duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retention_avg_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retention_curve: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    traffic_sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rpm_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    imported_from: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<YouTubeMetric id={self.id} publication_id={self.publication_id} views={self.views}>"


class AnalyticsInsight(BaseORM):
    """Insight từ chuỗi metrics → insights (learning loop, docs/13 + docs/05)."""

    __tablename__ = "analytics_insights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    movie_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("movies.id", ondelete="SET NULL"), index=True, nullable=True
    )
    publication_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("publications.id", ondelete="SET NULL"), index=True, nullable=True
    )
    scope: Mapped[str] = mapped_column(String(16), default="global", nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    insight: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signal_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strategy_version: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    def __repr__(self) -> str:
        return f"<AnalyticsInsight id={self.id} category={self.category} status={self.status}>"


class Experiment(BaseORM):
    """Thí nghiệm chiến lược: bộ trọng số strategy (docs/13 learning loop).

    status: proposed (từ Analytics Agent) / active (đang ảnh hưởng scoring) / archived.
    Khi active, Opportunity scoring dùng weights + strategy_version của nó.
    """

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategy_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    weights: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} strategy_version={self.strategy_version} status={self.status}>"


class KPISnapshot(BaseORM):
    """Snapshot KPI tổng kênh (docs/03: kpi_snapshots) — tạo mỗi lần refresh metrics."""

    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_ctr_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_watch_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_retention_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_rpm_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<KPISnapshot id={self.id} owner_id={self.owner_id} total_views={self.total_views}>"