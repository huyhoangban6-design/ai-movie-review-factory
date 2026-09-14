import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.helpers import load_script_for_owner
from app.core.database import get_db
from app.models.assets import Asset, CopyrightReview, RiskLevel
from app.models.job import Job, JobType
from app.models.user import User
from app.schemas.api import CopyrightEvaluateOut
from app.schemas.visual import (
    CopyrightEvaluateRequest,
    CopyrightEvaluateResult,
    CopyrightReviewOutput,
)
from app.services.factory import get_copyright_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success

router = APIRouter(prefix="/copyright", tags=["copyright"])


@router.post("/evaluate", response_model=CopyrightEvaluateOut, status_code=status.HTTP_201_CREATED)
def evaluate_copyright(
    payload: CopyrightEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopyrightEvaluateOut:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    if payload.asset_ids:
        assets = list(
            db.scalars(
                select(Asset).where(
                    Asset.script_id == script.id, Asset.id.in_(payload.asset_ids)
                )
            )
        )
    else:
        assets = list(
            db.scalars(select(Asset).where(Asset.script_id == script.id).order_by(Asset.segment_index))
        )

    if not assets:
        raise HTTPException(
            status_code=422,
            detail="Chưa có asset nào để đánh giá. Chạy POST /assets/generate trước.",
        )

    key = hashlib.sha256(f"{script.id}|copyright|{len(assets)}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.COPYRIGHT,
        idempotency_key=f"{current_user.id}:copyright:{key}",
        project_id=project_id,
        input_payload={"script_id": script.id, "asset_ids": payload.asset_ids},
    )

    provider = get_copyright_provider()
    reviews_out: list[CopyrightReviewOutput] = []
    human_review_count = 0
    blocked_count = 0

    for asset in assets:
        db.execute(delete(CopyrightReview).where(CopyrightReview.asset_id == asset.id))
        out = provider.evaluate(asset)
        review = CopyrightReview(
            asset_id=asset.id,
            risk_level=RiskLevel(out.risk_level),
            duration_warning=out.duration_warning,
            human_review_required=out.human_review_required,
            policy_notes=out.policy_notes,
            decision=out.decision,
            notes=out.notes,
        )
        db.add(review)
        reviews_out.append(out)
        if out.human_review_required:
            human_review_count += 1
        if out.decision == "block":
            blocked_count += 1

    script.pipeline_status = "copyright"
    db.flush()

    result = CopyrightEvaluateResult(
        script_id=script.id,
        reviews=reviews_out,
        human_review_count=human_review_count,
        blocked_count=blocked_count,
    )
    mark_job_success(db, job, result.model_dump())
    db.commit()

    return CopyrightEvaluateOut(job_id=job.id, script_id=script.id, result=result)