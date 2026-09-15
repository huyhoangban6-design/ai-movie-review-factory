from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.cost import CostRecord
from app.models.job import JobType
from app.models.project import Project
from app.models.user import User
from app.schemas.api import ProjectOut
from app.schemas.cost import (
    CostAlertOut,
    CostEstimateOut,
    CostEstimateRequest,
    CostRecordCreate,
    CostRecordOut,
    ProjectBudgetUpdate,
    ProjectCostSummaryOut,
)
from app.services.cost import (
    estimate_cost,
    project_cost_summary,
    recent_cost_alerts,
    record_cost,
)

router = APIRouter(tags=["cost"])


def _load_project_owned(db: Session, project_id: int, owner_id: int) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/cost/estimate", response_model=CostEstimateOut)
def get_cost_estimate(
    payload: CostEstimateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostEstimateOut:
    """Ước tính chi phí trước khi chạy job (docs/11). Offline = deterministic."""
    try:
        job_type = JobType(payload.job_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"job_type không hợp lệ: {payload.job_type} (không thuộc {[t.value for t in JobType]})",
        ) from exc
    rate, estimated, unit, category = estimate_cost(
        job_type,
        payload.units,
        payload.provider,
        payload.model,
        payload.mode,
    )
    return CostEstimateOut(
        job_type=job_type.value,
        provider=payload.provider,
        model=payload.model,
        mode=payload.mode,
        unit=unit,
        units=payload.units,
        unit_rate_usd=round(rate, 10),
        estimated_cost_usd=estimated,
        category=category,
    )


@router.get("/projects/{project_id}/cost", response_model=ProjectCostSummaryOut)
def get_project_cost_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectCostSummaryOut:
    """Tổng quan chi phí + budget của 1 project (docs/07 dashboard yêu cầu budget/cost)."""
    _load_project_owned(db, project_id, current_user.id)
    summary = project_cost_summary(db, project_id)
    project = db.get(Project, project_id)
    return ProjectCostSummaryOut(
        project_id=project_id,
        title=project.title if project else "",
        cost_mode=str(summary["cost_mode"]),
        max_cost_per_video=summary["max_cost_per_video"],
        total_estimated_usd=summary["total_estimated_usd"],
        total_actual_usd=summary["total_actual_usd"],
        remaining_budget=summary["remaining_budget"],
        budget_percent_used=summary["budget_percent_used"],
        per_category=summary["per_category"],
        per_provider=summary["per_provider"],
        alerts=summary["alerts"],
        records=[CostRecordOut.model_validate(r, from_attributes=True) for r in summary["records"]],
    )


@router.patch("/projects/{project_id}/budget", response_model=ProjectOut)
def update_project_budget(
    project_id: int,
    payload: ProjectBudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    """Cập nhật budget (max_cost_per_video) hoặc cost_mode của project."""
    project = _load_project_owned(db, project_id, current_user.id)
    if payload.max_cost_per_video is not None:
        project.max_cost_per_video = payload.max_cost_per_video
    if payload.cost_mode is not None:
        project.cost_mode = payload.cost_mode
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project, from_attributes=True)


@router.post("/cost/records", response_model=CostRecordOut, status_code=201)
def create_cost_record(
    payload: CostRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostRecordOut:
    """Ghi nhận chi phí thủ công / ngoài pipeline (hoá đơn provider thật)."""
    project_id = payload.project_id
    if project_id is not None:
        _load_project_owned(db, project_id, current_user.id)
    try:
        JobType(payload.job_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"job_type không hợp lệ: {payload.job_type}") from exc

    rec = record_cost(
        db,
        owner_id=current_user.id,
        project_id=project_id,
        job_id=payload.job_id,
        job_type=payload.job_type,
        provider=payload.provider,
        model=payload.model,
        mode=payload.mode,
        category=payload.category,
        unit=payload.unit,
        units=payload.units,
        unit_rate_usd=payload.unit_rate_usd,
        estimated_cost_usd=payload.estimated_cost_usd,
        actual_cost_usd=payload.actual_cost_usd,
        status=payload.status,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(rec)
    return CostRecordOut.model_validate(rec, from_attributes=True)


@router.get("/cost/records", response_model=list[CostRecordOut])
def list_cost_records(
    project_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CostRecordOut]:
    q = select(CostRecord).where(CostRecord.owner_id == current_user.id)
    if project_id is not None:
        _load_project_owned(db, project_id, current_user.id)
        q = q.where(CostRecord.project_id == project_id)
    q = q.order_by(CostRecord.id.desc()).limit(limit)
    return [CostRecordOut.model_validate(r, from_attributes=True) for r in db.scalars(q)]


@router.get("/cost/alerts", response_model=list[CostAlertOut])
def get_cost_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CostAlertOut]:
    """Các cảnh báo chi phí/budget gần đây (docs/11 cost alerts)."""
    return recent_cost_alerts(db, current_user.id)