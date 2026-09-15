"""Cost Engine — phases 8 (docs/03, docs/04, docs/11).

Tracks estimated / actual costs per provider/model/job, enforces per-project
budget limits, and provides cost summaries for the project detail screen.
Offline provider = zero-ish deterministic rates (safe defaults).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cost import CostMode, CostRecord, CostRecordStatus, SystemLog
from app.models.job import Job, JobType

log = logging.getLogger("app.cost")

# ── modes & multipliers ──────────────────────────────────────────────────────
COST_MODE_MULTIPLIER: dict[str, float] = {
    CostMode.FREE.value: 0.5,
    CostMode.BALANCED.value: 1.0,
    CostMode.PREMIUM.value: 1.5,
}

JOB_TYPE_CATEGORY: dict[JobType, str] = {
    JobType.MOVIE_RESEARCH: "research",
    JobType.OPPORTUNITY_SCORE: "research",
    JobType.CONTENT_ANGLE: "research",
    JobType.SCRIPT: "content",
    JobType.VOICE: "voice",
    JobType.TIMELINE: "content",
    JobType.ASSETS: "asset",
    JobType.COPYRIGHT: "asset",
    JobType.RENDER: "render",
    JobType.SUBTITLE: "content",
    JobType.QA: "content",
    JobType.UPLOAD: "publishing",
    JobType.PUBLISH: "publishing",
    JobType.ANALYTICS: "analytics",
    JobType.COMPETITOR_RESEARCH: "analytics",
    JobType.LEARN: "analytics",
    JobType.MOVIE_DISCOVERY: "research",
}

# ── default unit / rate (USD) — safe offline defaults ───────────────────────
DEFAULT_RATES: dict[JobType, tuple[str, float]] = {
    # (unit, rate_per_unit)
    JobType.MOVIE_RESEARCH:   ("job", 0.0005),
    JobType.OPPORTUNITY_SCORE: ("job", 0.0001),
    JobType.CONTENT_ANGLE:    ("job", 0.0002),
    JobType.SCRIPT:           ("job", 0.0010),
    JobType.VOICE:            ("chars", 0.000001),   # default; overridden by VoiceProvider.cost_per_1k_chars
    JobType.TIMELINE:         ("job", 0.0002),
    JobType.ASSETS:           ("asset", 0.0002),
    JobType.COPYRIGHT:        ("asset", 0.0001),
    JobType.RENDER:           ("minute", 0.0010),
    JobType.SUBTITLE:         ("job", 0.0002),
    JobType.QA:               ("job", 0.0002),
    JobType.UPLOAD:           ("job", 0.0002),
    JobType.PUBLISH:          ("job", 0.0002),
    JobType.ANALYTICS:        ("job", 0.0001),
    JobType.COMPETITOR_RESEARCH: ("job", 0.0002),
    JobType.LEARN:            ("job", 0.0002),
    JobType.MOVIE_DISCOVERY:  ("job", 0.0001),
}


def get_unit_rate(
    job_type: JobType,
    provider: str = "offline",
    model: str | None = None,
) -> tuple[str, float]:
    """Return (unit, rate_per_unit) for a given job+provider.

    Voice provider rate overrides defaults when `VoiceProvider.cost_per_1k_chars`
    is set; render uses env-overridable cost_rate_render_per_minute.
    """
    if job_type == JobType.VOICE and provider == "offline":
        rate_per_1k = settings.cost_rate_voice_per_1k_chars
        return ("chars", rate_per_1k / 1000.0)
    if job_type == JobType.RENDER and provider == "offline":
        return ("minute", settings.cost_rate_render_per_minute)
    return DEFAULT_RATES[job_type]


def estimate_cost(
    job_type: JobType,
    units: float = 1.0,
    provider: str = "offline",
    model: str | None = None,
    mode: str = CostMode.BALANCED.value,
) -> tuple[float, float, str, str]:
    """Return (unit_rate, estimated_cost_usd, unit, category)."""
    unit, rate = get_unit_rate(job_type, provider, model)
    multiplier = COST_MODE_MULTIPLIER.get(mode, 1.0)
    estimated = round(units * rate * multiplier, 8)
    category = JOB_TYPE_CATEGORY.get(job_type, "other")
    return rate, estimated, unit, category


# ── DB helpers ───────────────────────────────────────────────────────────────

def record_cost(
    db: Session,
    *,
    owner_id: int,
    project_id: int | None,
    job_id: int | None,
    job_type: str,
    provider: str,
    model: str | None,
    mode: str,
    category: str,
    unit: str,
    units: float,
    unit_rate_usd: float,
    estimated_cost_usd: float,
    actual_cost_usd: float,
    status: str = CostRecordStatus.RECORDED.value,
    notes: str | None = None,
) -> CostRecord:
    rec = CostRecord(
        owner_id=owner_id,
        project_id=project_id,
        job_id=job_id,
        job_type=job_type,
        provider=provider,
        model=model,
        mode=mode,
        category=category,
        unit=unit,
        units=units,
        unit_rate_usd=unit_rate_usd,
        estimated_cost_usd=estimated_cost_usd,
        actual_cost_usd=actual_cost_usd,
        status=status,
        notes=notes,
    )
    db.add(rec)
    db.flush()
    return rec


def record_job_cost(
    db: Session,
    job: Job,
    provider: str = "offline",
    model: str | None = None,
    units: float | None = None,
) -> CostRecord | None:
    """Record actual cost for a completed job and set job.cost_usd.

    If project exists, its cost_mode is used; else the global default.
    Returns the CostRecord or None if job_type not tracked.
    """
    try:
        jtype = JobType(job.job_type) if isinstance(job.job_type, str) else job.job_type
    except ValueError:
        return None

    # resolve mode
    mode = settings.cost_mode_default
    if job.project_id:
        from app.models.project import Project
        proj = db.get(Project, job.project_id)
        if proj and proj.cost_mode:
            mode = proj.cost_mode

    u = units if units and units > 0 else 1.0
    unit_rate, estimated, unit, category = estimate_cost(jtype, u, provider, model, mode)
    actual = estimated  # offline == estimated; real provider may differ

    rec = record_cost(
        db,
        owner_id=job.owner_id,
        project_id=job.project_id,
        job_id=job.id,
        job_type=jtype.value,
        provider=provider,
        model=model,
        mode=mode,
        category=category,
        unit=unit,
        units=u,
        unit_rate_usd=unit_rate,
        estimated_cost_usd=estimated,
        actual_cost_usd=actual,
        status=CostRecordStatus.RECORDED.value,
    )
    job.cost_usd = actual
    job.provider_name = provider
    db.flush()
    return rec


# ── budget enforcement ───────────────────────────────────────────────────────

def check_budget(db: Session, project_id: int | None, units: float = 1.0,
                 job_type: JobType = JobType.SCRIPT, provider: str = "offline",
                 model: str | None = None) -> tuple[float, float | None, bool, str]:
    """Compute budget check: returns (estimate, max_cost, exceeded, message).

    Raises HTTPException 402 if estimate > max_cost_per_video.
    Returns (estimate, None, False, "no_limit") if no max set.
    """
    mode = settings.cost_mode_default
    if project_id:
        from app.models.project import Project
        proj = db.get(Project, project_id)
        if proj:
            mode = proj.cost_mode or settings.cost_mode_default

    _, estimate, _, _ = estimate_cost(job_type, units, provider, model, mode)
    max_cost = None
    if project_id:
        from app.models.project import Project
        proj = db.get(Project, project_id)
        if proj and proj.max_cost_per_video:
            max_cost = float(proj.max_cost_per_video)

    if max_cost is None:
        return estimate, None, False, "no_limit"

    if estimate > max_cost:
        msg = (
            f"Chi phí ước tính ${estimate:.6f} vượt ngưỡng ${max_cost:.2f}/video. "
            "Cần duyệt thủ công hoặc nâng budget (PATCH /projects/{project_id}/budget)."
        )
        raise HTTPException(status_code=402, detail=msg)

    # cost alert when near threshold
    total_spent = total_actual_cost(db, project_id)
    if max_cost > 0 and (total_spent + estimate) / max_cost >= settings.cost_alert_threshold_pct:
        _write_cost_alert(
            db,
            project_id=project_id,
            message=(
                f"Chi phí dự án #{project_id} sắp đạt ngưỡng: "
                f"${total_spent:.6f} + ước tính ${estimate:.6f} = "
                f"${total_spent + estimate:.6f} / ${max_cost:.2f} "
                f"({((total_spent + estimate) / max_cost * 100):.1f}%)"
            ),
        )

    return estimate, max_cost, False, "ok"


def total_actual_cost(db: Session, project_id: int) -> float:
    """Total actual cost for all recorded cost_records of a project."""
    total = db.scalar(
        select(func.coalesce(func.sum(CostRecord.actual_cost_usd), 0.0)).where(
            CostRecord.project_id == project_id
        )
    ) or 0.0
    return round(float(total), 6)


def total_estimated_cost(db: Session, project_id: int) -> float:
    total = db.scalar(
        select(func.coalesce(func.sum(CostRecord.estimated_cost_usd), 0.0)).where(
            CostRecord.project_id == project_id
        )
    ) or 0.0
    return round(float(total), 6)


def per_category_cost(db: Session, project_id: int) -> dict[str, float]:
    rows = db.execute(
        select(CostRecord.category, func.sum(CostRecord.actual_cost_usd))
        .where(CostRecord.project_id == project_id)
        .group_by(CostRecord.category)
    ).all()
    return {cat: round(float(total), 6) for cat, total in rows}


def per_provider_cost(db: Session, project_id: int) -> dict[str, float]:
    rows = db.execute(
        select(CostRecord.provider, func.sum(CostRecord.actual_cost_usd))
        .where(CostRecord.project_id == project_id)
        .group_by(CostRecord.provider)
    ).all()
    return {prov: round(float(total), 6) for prov, total in rows}


def project_cost_summary(db: Session, project_id: int) -> dict[str, Any]:
    from app.models.project import Project

    proj = db.get(Project, project_id)
    max_cost = float(proj.max_cost_per_video) if proj and proj.max_cost_per_video else None
    actual = total_actual_cost(db, project_id)
    estimated = total_estimated_cost(db, project_id)
    remaining = (max_cost - actual) if max_cost is not None else None
    pct_used = round((actual / max_cost) * 100, 2) if max_cost and max_cost > 0 else None
    alerts: list[str] = []
    if max_cost and pct_used is not None:
        if pct_used >= 100:
            alerts.append(f"BUDGET_EXCEEDED: ${actual:.6f} / ${max_cost:.2f}")
        elif pct_used >= settings.cost_alert_threshold_pct * 100:
            alerts.append(f"BUDGET_WARNING: ${actual:.6f} / ${max_cost:.2f} ({pct_used:.1f}%)")

    records = list(
        db.scalars(
            select(CostRecord)
            .where(CostRecord.project_id == project_id)
            .order_by(CostRecord.id.desc())
            .limit(20)
        )
    )
    return {
        "project_id": project_id,
        "title": proj.title if proj else "",
        "cost_mode": (proj.cost_mode if proj else settings.cost_mode_default),
        "max_cost_per_video": max_cost,
        "total_estimated_usd": estimated,
        "total_actual_usd": actual,
        "remaining_budget": remaining,
        "budget_percent_used": pct_used,
        "per_category": per_category_cost(db, project_id),
        "per_provider": per_provider_cost(db, project_id),
        "alerts": alerts,
        "records": records,
    }


# ── cost alerts ──────────────────────────────────────────────────────────────

def _write_cost_alert(db: Session, project_id: int, message: str) -> None:
    log.warning("Cost alert project=%s: %s", project_id, message)
    db.add(
        SystemLog(
            level="warning",
            logger="app.cost",
            event="budget_alert",
            message=message,
            details={"project_id": project_id},
        )
    )
    db.flush()


def recent_cost_alerts(db: Session, owner_id: int) -> list[dict[str, Any]]:
    """Return recent budget alerts for user's projects."""
    rows = (
        db.execute(
            select(SystemLog)
            .where(SystemLog.event == "budget_alert")
            .order_by(SystemLog.occurred_at.desc(), SystemLog.id.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return [
        {"id": r.id, "level": r.level, "message": r.message,
         "details": r.details, "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None}
        for r in rows
    ]
