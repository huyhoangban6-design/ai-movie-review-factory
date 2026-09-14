import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.helpers import load_script_for_owner
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.user import User
from app.schemas.api import VisualPlanRequest, VisualPlanResult
from app.schemas.visual import VisualPlanMetadata
from app.services.factory import get_visual_planner_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success

router = APIRouter(prefix="/visual", tags=["visual"])


@router.post("/plan", response_model=VisualPlanResult, status_code=status.HTTP_201_CREATED)
def create_visual_plan(
    payload: VisualPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VisualPlanResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    key = hashlib.sha256(f"{script.id}|visual".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.ASSETS,
        idempotency_key=f"{current_user.id}:visualplan:{key}",
        project_id=project_id,
        input_payload={"script_id": script.id},
    )

    try:
        provider = get_visual_planner_provider()
        segments = sorted(script.segments, key=lambda s: s.position)
        plan = provider.plan(segments)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Visual planning failed: {e}")

    script.visual_plan = [s.model_dump() for s in plan.segments]
    script.pipeline_status = "visual_plan"
    db.flush()

    mark_job_success(db, job, plan.model_dump())
    db.commit()

    return VisualPlanResult(
        job_id=job.id,
        script_id=script.id,
        visual_plan=VisualPlanMetadata(
            strategy_version=plan.strategy_version,
            total_planned_duration_s=plan.total_planned_duration_s,
            segments=[s for s in plan.segments],
        ),
        pipeline_status="visual_plan",
    )