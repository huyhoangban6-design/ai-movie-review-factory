from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.analytics import AnalyticsInsight, Experiment, KPISnapshot, YouTubeMetric
from app.models.job import JobType
from app.models.movie import Competitor, CompetitorVideo, Movie
from app.models.production import VideoRender
from app.models.publishing import Publication, PublicationStatus
from app.models.scripting import Script
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsHistoryOut,
    AnalyticsSummaryOut,
    AnalyticsVideoOut,
    CompetitorOut,
    CompetitorResearchRequest,
    CompetitorResearchResult,
    CompetitorsOutput,
    CompetitorVideoOut,
    ExperimentActivateResult,
    ExperimentCreate,
    ExperimentOut,
    InsightOut,
    LearnRequest,
    LearnResult,
    StrategyOut,
    VideoMetricsOut,
    VideoMetricsResult,
    VideoMetricsOutput,
)
from app.services.factory import get_analytics_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key
from app.services.strategy import get_active_strategy

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Trạng thái publication không còn "sống" để kéo metrics.
_DEAD_STATUSES = (PublicationStatus.REJECTED, PublicationStatus.FAILED)


def _load_publication(db: Session, publication_id: int, owner_id: int) -> Publication:
    pub = db.scalar(
        select(Publication).where(Publication.id == publication_id, Publication.owner_id == owner_id)
    )
    if pub is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    return pub


def _load_movie(db: Session, movie_id: int, owner_id: int) -> Movie:
    movie = db.scalar(select(Movie).where(Movie.id == movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


def _renderer_duration(db: Session, publication: Publication) -> float | None:
    if publication.render_id is None:
        return None
    render = db.get(VideoRender, publication.render_id)
    return render.duration_s if render else None


def _latest_metric(db: Session, publication_id: int) -> YouTubeMetric | None:
    return db.scalar(
        select(YouTubeMetric)
        .where(YouTubeMetric.publication_id == publication_id)
        .order_by(YouTubeMetric.id.desc())
    )


def _latest_metrics_per_publication(
    db: Session, owner_id: int, movie_id: int | None = None
) -> list[YouTubeMetric]:
    """Snapshot mới nhất của từng video (tránh double-count khi có nhiều lần refresh)."""
    latest_ids = (
        select(func.max(YouTubeMetric.id).label("id"))
        .where(YouTubeMetric.owner_id == owner_id)
        .group_by(YouTubeMetric.publication_id)
        .subquery()
    )
    q = (
        select(YouTubeMetric)
        .join(latest_ids, YouTubeMetric.id == latest_ids.c.id)
        .order_by(YouTubeMetric.publication_id)
    )
    if movie_id is not None:
        q = (
            q.join(Publication, Publication.id == YouTubeMetric.publication_id)
            .join(Script, Script.id == Publication.script_id)
            .where(Script.movie_id == movie_id)
        )
    return list(db.scalars(q))


def _write_kpi_snapshot(db: Session, owner_id: int) -> KPISnapshot:
    latest = _latest_metrics_per_publication(db, owner_id)
    total_views = sum(m.views for m in latest)
    total_impressions = sum(m.impressions for m in latest)
    total_clicks = sum(m.clicks for m in latest)
    total_watch = sum(m.watch_time_hours for m in latest)
    total_likes = sum(m.likes for m in latest)
    total_comments = sum(m.comments for m in latest)
    total_revenue = round(sum(m.revenue_usd for m in latest), 2)
    rows = len(latest)
    snapshot = KPISnapshot(
        owner_id=owner_id,
        captured_at=datetime.now(timezone.utc),
        published_video_count=rows,
        total_views=total_views,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        avg_ctr_pct=round(total_clicks / total_impressions * 100, 2) if total_impressions else None,
        total_watch_time_hours=round(total_watch, 2),
        avg_retention_pct=round(sum(m.retention_avg_pct or 0 for m in latest) / rows, 2) if rows else None,
        total_likes=total_likes,
        total_comments=total_comments,
        total_revenue_usd=total_revenue,
        avg_rpm_usd=round(total_revenue / total_views * 1000, 2) if total_views else None,
        data={"provider": get_analytics_provider().name, "simulated": True},
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _to_metric_schema(m: YouTubeMetric) -> VideoMetricsOut:
    return VideoMetricsOut.model_validate(m, from_attributes=True)


@router.post("/video/{publication_id}/refresh", response_model=VideoMetricsResult, status_code=status.HTTP_201_CREATED)
def refresh_video_metrics(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoMetricsResult:
    """Kéo metrics 1 video (docs/04 GET /analytics/video + docs/13). Offline = deterministic sample."""
    publication = _load_publication(db, publication_id, current_user.id)
    if publication.status in _DEAD_STATUSES:
        raise HTTPException(status_code=422, detail=f"Publication đang ở trạng thái {publication.status.value} — không kéo metrics được.")
    if not publication.youtube_video_id:
        raise HTTPException(status_code=422, detail="Publication chưa có youtube_video_id (chưa upload).")

    job = create_job(
        db,
        current_user.id,
        JobType.ANALYTICS,
        idempotency_key=next_attempt_key(
            db, current_user.id, JobType.ANALYTICS, f"metrics:{publication.id}"
        ),
        project_id=publication.project_id,
        input_payload={"publication_id": publication.id, "video_id": publication.youtube_video_id},
    )

    try:
        provider = get_analytics_provider()
        output: VideoMetricsOutput = provider.fetch_metrics(
            publication.id,
            publication.youtube_video_id,
            publication.title,
            _renderer_duration(db, publication),
            datetime.now(timezone.utc),
        )
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analytics refresh failed: {e}")

    metric = YouTubeMetric(
        publication_id=publication.id,
        owner_id=current_user.id,
        video_id=output.video_id,
        captured_at=output.captured_at,
        views=output.views,
        impressions=output.impressions,
        clicks=output.clicks,
        ctr_pct=output.ctr_pct,
        likes=output.likes,
        comments=output.comments,
        watch_time_hours=output.watch_time_hours,
        avg_view_duration_s=output.avg_view_duration_s,
        retention_avg_pct=output.retention_avg_pct,
        retention_curve=output.retention_curve,
        traffic_sources=output.traffic_sources,
        subscribers_gained=output.subscribers_gained,
        revenue_usd=output.revenue_usd,
        rpm_usd=output.rpm_usd,
        imported_from=output.imported_from,
        data=output.metadata,
    )
    db.add(metric)
    db.flush()

    _write_kpi_snapshot(db, current_user.id)

    mark_job_success(db, job, output)
    db.commit()

    return VideoMetricsResult(
        job_id=job.id,
        publication_id=publication.id,
        snapshot_id=metric.id,
        metrics=_to_metric_schema(metric),
    )


@router.get("/video/{publication_id}", response_model=AnalyticsVideoOut)
def get_video_metrics(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsVideoOut:
    """Trả metrics mới nhất; chưa có snapshot thì derive deterministic (không ghi DB)."""
    publication = _load_publication(db, publication_id, current_user.id)
    stored = _latest_metric(db, publication.id)
    if stored is not None:
        return AnalyticsVideoOut(
            publication_id=publication.id,
            video_id=publication.youtube_video_id,
            title=publication.title,
            status=publication.status.value,
            metrics=_to_metric_schema(stored),
            source="stored",
        )

    provider = get_analytics_provider()
    output = provider.fetch_metrics(
        publication.id,
        publication.youtube_video_id or "",
        publication.title,
        _renderer_duration(db, publication),
        None,
    )
    data = output.model_dump()
    data["id"] = 0
    data["publication_id"] = publication.id
    data["created_at"] = datetime.now(timezone.utc)
    del data["imported_from"]
    del data["simulated"]
    del data["metadata"]
    return AnalyticsVideoOut(
        publication_id=publication.id,
        video_id=publication.youtube_video_id,
        title=publication.title,
        status=publication.status.value,
        metrics=VideoMetricsOut(**data),
        source="derived",
    )


@router.get("/video/{publication_id}/history", response_model=AnalyticsHistoryOut)
def get_video_metrics_history(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsHistoryOut:
    publication = _load_publication(db, publication_id, current_user.id)
    snapshots = list(
        db.scalars(
            select(YouTubeMetric)
            .where(YouTubeMetric.publication_id == publication.id)
            .order_by(YouTubeMetric.id.desc())
        )
    )
    return AnalyticsHistoryOut(
        publication_id=publication.id,
        snapshots=[_to_metric_schema(m) for m in snapshots],
    )


@router.get("/summary", response_model=AnalyticsSummaryOut)
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummaryOut:
    latest = _latest_metrics_per_publication(db, current_user.id)
    total_views = sum(m.views for m in latest)
    total_impressions = sum(m.impressions for m in latest)
    total_clicks = sum(m.clicks for m in latest)
    total_watch = round(sum(m.watch_time_hours for m in latest), 2)
    total_likes = sum(m.likes for m in latest)
    total_comments = sum(m.comments for m in latest)
    total_revenue = round(sum(m.revenue_usd for m in latest), 2)
    rows = len(latest)
    insight_count = db.scalar(
        select(func.count(AnalyticsInsight.id)).where(AnalyticsInsight.owner_id == current_user.id)
    ) or 0
    return AnalyticsSummaryOut(
        video_count=rows,
        total_views=total_views,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        avg_ctr_pct=round(total_clicks / total_impressions * 100, 2) if total_impressions else 0.0,
        total_watch_time_hours=total_watch,
        avg_retention_pct=round(sum(m.retention_avg_pct or 0 for m in latest) / rows, 2) if rows else 0.0,
        total_likes=total_likes,
        total_comments=total_comments,
        total_revenue_usd=total_revenue,
        avg_rpm_usd=round(total_revenue / total_views * 1000, 2) if total_views else 0.0,
        insight_count=insight_count,
    )


@router.post("/competitors/research", response_model=CompetitorResearchResult, status_code=status.HTTP_201_CREATED)
def research_competitors(
    payload: CompetitorResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorResearchResult:
    """Nghiên cứu đối thủ qua analytics (docs/13; bảng competitors/competitor_videos từ Phase 2).

    Replace: xoá competitor cũ của movie (cascade competitor_videos) rồi viết lại.
    """
    movie = _load_movie(db, payload.movie_id, current_user.id)

    job = create_job(
        db,
        current_user.id,
        JobType.COMPETITOR_RESEARCH,
        idempotency_key=next_attempt_key(
            db, current_user.id, JobType.COMPETITOR_RESEARCH, f"competitors:{movie.id}"
        ),
        project_id=movie.project_id,
        input_payload={"movie_id": movie.id, "title": movie.title},
    )

    try:
        provider = get_analytics_provider()
        rows = provider.research_competitors(movie.id, movie.title, movie.year)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Competitor research failed: {e}")

    old = list(db.scalars(select(Competitor).where(Competitor.movie_id == movie.id)))
    for comp in old:
        db.delete(comp)
    db.flush()

    created: list[CompetitorOut] = []
    for row in rows:
        comp = Competitor(
            movie_id=movie.id,
            channel=row["channel"],
            genre=row.get("genre"),
            influence=row.get("influence"),
            top_videos=row.get("top_videos"),
        )
        db.add(comp)
        db.flush()
        for v in row.get("videos", []):
            db.add(
                CompetitorVideo(
                    competitor_id=comp.id,
                    movie_title=v.get("movie_title"),
                    score=v.get("score"),
                    influence=v.get("influence"),
                    view_count=v.get("view_count"),
                    retrieval_url=v.get("retrieval_url"),
                )
            )
        created.append(CompetitorOut(id=comp.id, channel=row["channel"], genre=row.get("genre"), influence=row.get("influence"), top_videos=row.get("top_videos")))

    mark_job_success(db, job, {"movie_id": movie.id, "competitors": len(rows)})
    db.commit()
    return CompetitorResearchResult(job_id=job.id, movie_id=movie.id, competitors=created)


@router.get("/competitors", response_model=CompetitorsOutput)
def list_competitors(
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompetitorsOutput:
    movie = _load_movie(db, movie_id, current_user.id)
    competitors = list(
        db.scalars(select(Competitor).where(Competitor.movie_id == movie.id).order_by(Competitor.id))
    )
    out: list[CompetitorOut] = []
    for comp in competitors:
        videos = list(
            db.scalars(
                select(CompetitorVideo).where(CompetitorVideo.competitor_id == comp.id).order_by(CompetitorVideo.id)
            )
        )
        out.append(
            CompetitorOut(
                id=comp.id,
                channel=comp.channel,
                genre=comp.genre,
                influence=comp.influence,
                top_videos=comp.top_videos,
                videos=[CompetitorVideoOut.model_validate(v, from_attributes=True) for v in videos],
            )
        )
    return CompetitorsOutput(movie_id=movie.id, competitors=out)


@router.post("/learn", response_model=LearnResult, status_code=status.HTTP_201_CREATED)
def run_learning_loop(
    payload: LearnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearnResult:
    """Learning loop: metrics → insights → proposed strategy version (docs/13, docs/05)."""
    movie_id = None
    if payload.movie_id is not None:
        movie = _load_movie(db, payload.movie_id, current_user.id)
        movie_id = movie.id

    videos = _latest_metrics_per_publication(db, current_user.id, movie_id)
    scope = "movie" if movie_id is not None else "global"

    job = create_job(
        db,
        current_user.id,
        JobType.LEARN,
        idempotency_key=next_attempt_key(
            db, current_user.id, JobType.LEARN, f"learn:{movie_id or 'global'}"
        ),
        project_id=None,
        input_payload={"scope": scope, "movie_id": movie_id, "videos": len(videos)},
    )

    try:
        provider = get_analytics_provider()
        output = provider.derive_insights(videos, scope)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Learning loop failed: {e}")

    for insight in output.insights:
        db.add(
            AnalyticsInsight(
                owner_id=current_user.id,
                movie_id=movie_id,
                publication_id=insight.publication_id,
                scope=insight.scope,
                category=insight.category,
                insight=insight.insight,
                suggestion=insight.suggestion,
                signal_value=insight.signal_value,
                strategy_version=insight.strategy_version,
                status="open",
            )
        )

    proposed = output.proposed_strategy
    experiment = Experiment(
        owner_id=current_user.id,
        name=f"Autocalibration {proposed.strategy_version} ({scope})",
        description=proposed.rationale,
        strategy_version=proposed.strategy_version,
        weights=proposed.weights,
        status="proposed",
        stage="analytics_calibration",
    )
    db.add(experiment)
    db.flush()

    mark_job_success(db, job, {"insights": len(output.insights), "proposed_strategy": proposed.strategy_version})
    db.commit()

    return LearnResult(
        job_id=job.id,
        scope=scope,
        movie_id=movie_id,
        insight_count=len(output.insights),
        insights=output.insights,
        proposed_strategy=proposed,
    )


@router.get("/insights", response_model=list[InsightOut])
def list_insights(
    movie_id: int | None = None,
    status: str | None = "open",
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InsightOut]:
    q = select(AnalyticsInsight).where(AnalyticsInsight.owner_id == current_user.id)
    if movie_id is not None:
        q = q.where(AnalyticsInsight.movie_id == movie_id)
    if status is not None:
        q = q.where(AnalyticsInsight.status == status)
    q = q.order_by(AnalyticsInsight.id.desc()).limit(min(limit, 100))
    return [InsightOut.model_validate(i, from_attributes=True) for i in db.scalars(q)]


@router.get("/strategy", response_model=StrategyOut)
def get_strategy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyOut:
    version, weights, source, exp_id = get_active_strategy(db)
    return StrategyOut(
        strategy_version=version,
        weights=weights,
        source=source,
        experiment_id=exp_id,
        applied_to_scoring=True,
    )


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentOut]:
    experiments = list(
        db.scalars(
            select(Experiment)
            .where(Experiment.owner_id == current_user.id)
            .order_by(Experiment.id.desc())
        )
    )
    return [ExperimentOut.model_validate(e, from_attributes=True) for e in experiments]


@router.post("/experiments", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentOut:
    weights = payload.weights or None
    if not weights:
        raise HTTPException(status_code=422, detail="weights bắt buộc cho experiment (bộ trọng số calibration).")
    experiment = Experiment(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        strategy_version=payload.strategy_version,
        weights=weights,
        status="proposed",
        stage="manual",
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return ExperimentOut.model_validate(experiment, from_attributes=True)


@router.post("/experiments/{experiment_id}/activate", response_model=ExperimentActivateResult)
def activate_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentActivateResult:
    experiment = db.scalar(
        select(Experiment).where(Experiment.id == experiment_id, Experiment.owner_id == current_user.id)
    )
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.status == "active":
        return ExperimentActivateResult(
            experiment_id=experiment.id,
            strategy_version=experiment.strategy_version,
            status=experiment.status,
            detail="Experiment đã active — không đổi.",
        )

    others = list(
        db.scalars(
            select(Experiment)
            .where(Experiment.owner_id == current_user.id, Experiment.status == "active")
        )
    )
    for exp in others:
        exp.status = "archived"
    experiment.status = "active"
    experiment.activated_at = experiment.activated_at or datetime.now(timezone.utc)
    db.commit()
    return ExperimentActivateResult(
        experiment_id=experiment.id,
        strategy_version=experiment.strategy_version,
        status=experiment.status,
        detail="Đã kích hoạt experiment — Opportunity scoring dùng trọng số mới (docs/13).",
    )