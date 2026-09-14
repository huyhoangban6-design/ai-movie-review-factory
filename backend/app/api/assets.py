import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.helpers import load_script_for_owner
from app.core.config import settings
from app.core.database import get_db
from app.models.assets import Asset
from app.models.job import Job, JobType
from app.models.user import User
from app.schemas.api import (
    AssetGenerateResult,
    AssetSearchRequestOut,
)
from app.schemas.visual import (
    AssetActionResult,
    AssetCreate,
    AssetOut,
    AssetGenerateRequest,
    AssetSearchRequest,
    VisualPlanMetadata,
    VisualPlanSegment,
)
from app.services.factory import get_asset_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success

router = APIRouter(prefix="/assets", tags=["assets"])


def _load_plan(script) -> VisualPlanMetadata:
    if not script.visual_plan:
        raise HTTPException(
            status_code=422,
            detail="Chưa có visual plan. Chạy POST /visual/plan trước.",
        )
    return VisualPlanMetadata(
        strategy_version="v1",
        total_planned_duration_s=round(sum(float(p.get("duration_s", 0)) for p in script.visual_plan), 2),
        segments=[VisualPlanSegment(**p) for p in script.visual_plan],
    )


def _apply_assets(
    db: Session,
    script,
    owner_id: int,
    segment_index: int | None,
    source_hint: str,
) -> AssetActionResult:
    plan = _load_plan(script)
    provider = get_asset_provider()
    created: list[AssetCreate] = provider.acquire(plan, segment_index, source_hint)
    if not created:
        raise HTTPException(status_code=422, detail="Không có segment nào để tạo asset (kiểm tra visual plan).")

    # Replace assets của các segment mục tiêu để trạng thái luôn đồng bộ với plan mới nhất.
    targets = {c.segment_index for c in created}
    for idx in targets:
        db.execute(delete(Asset).where(Asset.script_id == script.id, Asset.segment_index == idx))

    assets_out: list[AssetOut] = []
    for c in created:
        asset = Asset(
            script_id=script.id,
            owner_id=owner_id,
            segment_index=c.segment_index,
            asset_type=c.asset_type,
            title=c.title,
            source=c.source,
            source_url=c.source_url,
            license=c.license,
            commercial_use=c.commercial_use,
            owner_name=c.owner_name,
            acquisition_time=c.acquisition_time,
            usage_context=c.usage_context,
            duration_s=c.duration_s,
            transformations=c.transformations,
            risk_score=c.risk_score,
            file_url=c.file_url,
            thumbnail_url=c.thumbnail_url,
        )
        db.add(asset)
        db.flush()
        assets_out.append(AssetOut(**c.model_dump(), id=asset.id, script_id=script.id))

    script.pipeline_status = "assets"
    db.flush()
    return AssetActionResult(script_id=script.id, assets_created=len(assets_out), assets=assets_out)


@router.post("/search", response_model=AssetSearchRequestOut, status_code=status.HTTP_201_CREATED)
def search_assets(
    payload: AssetSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetSearchRequestOut:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    key = hashlib.sha256(f"{script.id}|stock|{payload.segment_index}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.ASSETS,
        idempotency_key=f"{current_user.id}:assetsearch:{key}",
        project_id=project_id,
        input_payload={"script_id": script.id, "segment_index": payload.segment_index},
    )

    try:
        result = _apply_assets(db, script, current_user.id, payload.segment_index, "licensed_stock")
    except HTTPException:
        mark_job_failed(db, job, "Asset search failed (thiếu visual plan?)")
        db.commit()
        raise
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Asset search failed: {e}")

    mark_job_success(db, job, result.model_dump())
    db.commit()
    return AssetSearchRequestOut(script_id=script.id, result=result)


@router.post("/generate", response_model=AssetGenerateResult, status_code=status.HTTP_201_CREATED)
def generate_assets(
    payload: AssetGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetGenerateResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    key = hashlib.sha256(f"{script.id}|gen|{payload.segment_index}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.ASSETS,
        idempotency_key=f"{current_user.id}:assetgen:{key}",
        project_id=project_id,
        input_payload={"script_id": script.id, "segment_index": payload.segment_index},
    )

    try:
        result = _apply_assets(db, script, current_user.id, payload.segment_index, settings.asset_source_hint)
    except HTTPException:
        mark_job_failed(db, job, "Asset generation failed (thiếu visual plan?)")  # noqa: BLE001
        db.commit()
        raise
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Asset generation failed: {e}")

    mark_job_success(db, job, result.model_dump())
    db.commit()
    return AssetGenerateResult(job_id=job.id, script_id=script.id, result=result)