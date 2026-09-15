import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.helpers import load_script_for_owner
from app.core.database import get_db
from app.models.job import JobType
from app.models.production import QAGate, QAReport, RenderStatus, Subtitle, VideoRender
from app.models.publishing import Publication, PublicationStatus
from app.models.user import User
from app.schemas.publishing import (
    ApproveRequest,
    ApproveResult,
    PublishOutput,
    PublishRequest,
    PublishResult,
    PublicationOut,
    UploadOutput,
    UploadRequest,
    UploadResult,
)
from app.services.cost import check_budget, record_job_cost
from app.services.factory import get_publishing_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key

router = APIRouter(prefix="/youtube", tags=["youtube"])


def _latest_passing_qa(db: Session, script_id: int) -> QAReport | None:
    return db.scalar(
        select(QAReport)
        .where(QAReport.script_id == script_id, QAReport.gate == QAGate.FINAL)
        .order_by(QAReport.id.desc())
    )


def _latest_render(db: Session, script_id: int) -> VideoRender | None:
    return db.scalar(
        select(VideoRender).where(VideoRender.script_id == script_id).order_by(VideoRender.id.desc())
    )


def _latest_subtitle(db: Session, script_id: int) -> Subtitle | None:
    return db.scalar(
        select(Subtitle).where(Subtitle.script_id == script_id).order_by(Subtitle.id.desc())
    )


def _load_publication(db: Session, publication_id: int, owner_id: int) -> Publication:
    pub = db.scalar(select(Publication).where(Publication.id == publication_id, Publication.owner_id == owner_id))
    if pub is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    return pub


@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
def upload_to_youtube(
    payload: UploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    # Preconditions (docs/13 + docs/00 #8): package phải vượt Final QA + đủ render + subtitle.
    final = _latest_passing_qa(db, script.id)
    if final is None or not final.passed:
        raise HTTPException(status_code=422, detail="Chưa có Final QA pass. Chạy POST /video/qa và đạt final trước khi upload.")

    render = _latest_render(db, script.id)
    if render is None or render.status != RenderStatus.RENDERED or not render.video_url:
        raise HTTPException(status_code=422, detail="Chưa có render hoàn tất. Chạy POST /video/render trước.")

    subtitle = _latest_subtitle(db, script.id)
    if subtitle is None:
        raise HTTPException(status_code=422, detail="Chưa có phụ đề. Chạy POST /video/subtitle trước.")

    title = (payload.title or "").strip() or script.title

    # Phase 8 cost engine: budget gate trước khi upload (publishing tốn chi phí provider thật).
    check_budget(db, project_id, units=1.0, job_type=JobType.UPLOAD)

    key = hashlib.sha256(f"{script.id}|upload|{render.id}|{title}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.UPLOAD,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.UPLOAD, f"upload:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "render_id": render.id, "title": title, "privacy": payload.privacy.value},
    )

    try:
        provider = get_publishing_provider()
        output: UploadOutput = provider.upload(
            script.id,
            title,
            payload.description,
            payload.tags,
            render.video_url,
            payload.privacy.value,
            payload.notify_subscribers,
        )
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    publication = Publication(
        script_id=script.id,
        owner_id=current_user.id,
        render_id=render.id,
        project_id=project_id,
        status=PublicationStatus.PRIVATE_UPLOADED,
        youtube_video_id=output.youtube_video_id,
        title=title,
        description=payload.description,
        tags=payload.tags,
        privacy_status=output.privacy_status,
        published_url=output.video_url,
        notify_subscribers=payload.notify_subscribers,
        upload_metadata=output.upload_metadata,
    )
    db.add(publication)
    db.flush()

    script.pipeline_status = "upload"
    db.flush()

    mark_job_success(db, job, output)
    record_job_cost(db, job, provider=provider.name, units=1.0)
    db.commit()

    return UploadResult(job_id=job.id, publication_id=publication.id, script_id=script.id, upload=output)


@router.post("/approve", response_model=ApproveResult)
def approve_publication(
    payload: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApproveResult:
    publication = _load_publication(db, payload.publication_id, current_user.id)

    if publication.status in (PublicationStatus.PUBLISHED, PublicationStatus.SCHEDULED):
        raise HTTPException(status_code=409, detail="Publication đã publish/schedule — không duyệt tiếp được.")

    if payload.approved:
        if publication.status in (PublicationStatus.PRIVATE_UPLOADED, PublicationStatus.READY_TO_PUBLISH):
            publication.status = PublicationStatus.READY_TO_PUBLISH
        else:
            raise HTTPException(status_code=409, detail=f"Không thể duyệt publication đang ở trạng thái {publication.status.value}.")
        publication.approved = True
        publication.approval_note = payload.note
        publication.approved_at = publication.approved_at or datetime.now()
    else:
        publication.status = PublicationStatus.REJECTED
        publication.approved = False
        publication.approval_note = payload.note or "Bị từ chối ở checkpoint duyệt (CP6)."

    db.commit()
    return ApproveResult(publication_id=publication.id, status=publication.status.value, approved=publication.approved)


@router.post("/publish", response_model=PublishResult, status_code=status.HTTP_201_CREATED)
def publish_video(
    payload: PublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishResult:
    publication = _load_publication(db, payload.publication_id, current_user.id)

    # CP6: bắt buộc có human approval trước khi public/schedule (docs/13, docs/00 #8).
    if not publication.approved or publication.status != PublicationStatus.READY_TO_PUBLISH:
        raise HTTPException(
            status_code=422,
            detail="Chưa được duyệt (CP6). Chạy POST /youtube/approve với approved=true trước.",
        )
    script, project_id = load_script_for_owner(db, publication.script_id, current_user.id)

    # Phase 8 cost engine: budget gate trước khi publish.
    check_budget(db, publication.project_id or project_id, units=1.0, job_type=JobType.PUBLISH)

    key = hashlib.sha256(f"{publication.id}|publish|seed".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.PUBLISH,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.PUBLISH, f"publish:{key}"),
        project_id=publication.project_id or project_id,
        input_payload={"publication_id": publication.id, "privacy": payload.privacy.value, "publish_at": str(payload.publish_at) if payload.publish_at else None},
    )

    try:
        provider = get_publishing_provider()
        output: PublishOutput = provider.publish(
            publication.youtube_video_id or "",
            publication.title,
            payload.privacy.value,
            payload.publish_at,
        )
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Publish failed: {e}")

    if output.status == "scheduled" or payload.publish_at is not None:
        publication.status = PublicationStatus.SCHEDULED
    else:
        publication.status = PublicationStatus.PUBLISHED
    publication.privacy_status = payload.privacy.value
    publication.publish_at = output.publish_at
    publication.published_url = output.video_url
    db.flush()

    script.pipeline_status = "published"
    db.flush()

    mark_job_success(db, job, output)
    record_job_cost(db, job, provider=provider.name, units=1.0)
    db.commit()

    return PublishResult(job_id=job.id, publication_id=publication.id, script_id=script.id, publish=output)


@router.get("/publications/{publication_id}", response_model=PublicationOut)
def get_publication(
    publication_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> PublicationOut:
    return PublicationOut.model_validate(_load_publication(db, publication_id, current_user.id), from_attributes=True)
