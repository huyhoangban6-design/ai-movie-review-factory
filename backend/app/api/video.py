import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.helpers import load_script_for_owner
from app.core.config import settings
from app.core.database import get_db
from app.models.assets import Asset, CopyrightReview
from app.models.job import Job, JobType
from app.models.movie import MovieAnalysis
from app.models.production import QAReport, RenderStatus, Subtitle, VideoRender
from app.models.scripting import ScriptTimeline, VoiceGeneration
from app.models.user import User
from app.schemas.render import (
    QACheckItem,
    QAReportOutput,
    QAResult,
    QARequest,
    RenderOutput,
    RenderRequest,
    RenderResult,
    SubtitleOutput,
    SubtitleRequest,
    SubtitleResult,
)
from app.services.factory import get_qa_provider, get_render_provider, get_subtitle_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key

router = APIRouter(prefix="/video", tags=["video"])


def _latest_generation(db: Session, script_id: int) -> VoiceGeneration | None:
    return db.scalar(
        select(VoiceGeneration)
        .where(VoiceGeneration.script_id == script_id, VoiceGeneration.status == "completed")
        .order_by(VoiceGeneration.id.desc())
    )


def _latest_timeline(db: Session, script_id: int) -> ScriptTimeline | None:
    return db.scalar(
        select(ScriptTimeline)
        .where(ScriptTimeline.script_id == script_id)
        .order_by(ScriptTimeline.id.desc())
    )


@router.post("/render", response_model=RenderResult, status_code=status.HTTP_201_CREATED)
def render_video(
    payload: RenderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RenderResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    # Preconditions: voice + timeline (để audio/duration), visual plan + assets + copyright.
    generation = _latest_generation(db, script.id)
    if generation is None or not generation.audio_url or not generation.audio_duration_s:
        raise HTTPException(status_code=422, detail="Chưa có giọng đọc hoàn tất. Chạy POST /voice/generate trước.")

    if not script.visual_plan:
        raise HTTPException(status_code=422, detail="Chưa có visual plan. Chạy POST /visual/plan trước.")

    assets = list(db.scalars(select(Asset).where(Asset.script_id == script.id)))
    if not assets:
        raise HTTPException(status_code=422, detail="Chưa có asset. Chạy POST /assets/generate trước.")

    # Copyright gate: asset bị block không được vào final render (docs/09).
    asset_ids = [a.id for a in assets]
    reviews = list(db.scalars(select(CopyrightReview).where(CopyrightReview.asset_id.in_(asset_ids))))
    blocked = [r for r in reviews if r.decision == "block"]
    if blocked:
        raise HTTPException(
            status_code=422,
            detail=f"Có {len(blocked)} asset bị chặn bản quyền. Không render được. Chạy lại /copyright/evaluate sau khi thay asset.",
        )

    key = hashlib.sha256(f"{script.id}|render|{generation.id}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.RENDER,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.RENDER, f"render:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "generation_id": generation.id},
    )

    try:
        provider = get_render_provider()
        output = provider.render(script.id, generation.audio_url, float(generation.audio_duration_s))
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")

    render = VideoRender(
        script_id=script.id,
        owner_id=current_user.id,
        status=RenderStatus.RENDERED,
        video_url=output.video_url,
        thumbnail_url=output.thumbnail_url,
        output_path=output.output_path,
        audio_url=generation.audio_url,
        resolution=output.resolution,
        fps=output.fps,
        video_codec=output.video_codec,
        audio_codec=output.audio_codec,
        duration_s=output.duration_s,
        file_size_bytes=output.file_size_bytes,
        render_config={
            "provider": provider.name,
            "resolution": output.resolution,
            "fps": output.fps,
            "video_codec": output.video_codec,
            "audio_codec": output.audio_codec,
        },
        render_log="offline render: mux video (metadata) + audio track.",
    )
    db.add(render)
    db.flush()

    script.pipeline_status = "render"
    db.flush()

    mark_job_success(db, job, output.model_dump())
    db.commit()

    return RenderResult(job_id=job.id, render_id=render.id, script_id=script.id, render=output)


@router.post("/subtitle", response_model=SubtitleResult, status_code=status.HTTP_201_CREATED)
def build_subtitle(
    payload: SubtitleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubtitleResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    timeline = _latest_timeline(db, script.id)
    if timeline is None:
        raise HTTPException(status_code=422, detail="Chưa có timeline. Chạy POST /timeline/build trước.")

    generation = _latest_generation(db, script.id)
    if generation is None:
        raise HTTPException(status_code=422, detail="Chưa có giọng đọc. Chạy POST /voice/generate trước.")

    key = hashlib.sha256(f"{script.id}|srt|{timeline.id}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.SUBTITLE,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.SUBTITLE, f"subtitle:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "format": payload.format},
    )

    try:
        provider = get_subtitle_provider()
        output = provider.build(script.id, timeline, generation)
        output = output.model_copy(update={"format": payload.format})
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Subtitle generation failed: {e}")

    db.execute(delete(Subtitle).where(Subtitle.script_id == script.id))
    subtitle = Subtitle(
        script_id=script.id,
        owner_id=current_user.id,
        generation_id=generation.id,
        format=payload.format,
        language=output.language,
        content=output.content,
        duration_s=output.duration_s,
        cue_count=output.cue_count,
        status="completed",
    )
    db.add(subtitle)
    db.flush()

    script.pipeline_status = "subtitle"
    db.flush()

    mark_job_success(db, job, output.model_dump())
    db.commit()

    return SubtitleResult(job_id=job.id, subtitle_id=subtitle.id, script_id=script.id, subtitle=output)


@router.post("/qa", response_model=QAResult, status_code=status.HTTP_201_CREATED)
def run_qa(
    payload: QARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QAResult:
    script, project_id = load_script_for_owner(db, payload.script_id, current_user.id)

    render = db.scalar(
        select(VideoRender).where(VideoRender.script_id == script.id).order_by(VideoRender.id.desc())
    )
    if render is None:
        raise HTTPException(status_code=422, detail="Chưa có render. Chạy POST /video/render trước.")

    subtitle = db.scalar(
        select(Subtitle).where(Subtitle.script_id == script.id).order_by(Subtitle.id.desc())
    )
    if subtitle is None:
        raise HTTPException(status_code=422, detail="Chưa có subtitle. Chạy POST /video/subtitle trước.")

    assets = list(db.scalars(select(Asset).where(Asset.script_id == script.id)))
    asset_ids = [a.id for a in assets]
    reviews = (
        list(db.scalars(select(CopyrightReview).where(CopyrightReview.asset_id.in_(asset_ids))))
        if asset_ids
        else []
    )
    generation = _latest_generation(db, script.id)
    analysis = db.scalar(
        select(MovieAnalysis).where(MovieAnalysis.movie_id == script.movie_id).order_by(MovieAnalysis.id.desc())
    )
    has_facts = bool(analysis and (analysis.facts or analysis.summary))

    key = hashlib.sha256(f"{script.id}|qa|{render.id}|{subtitle.id}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.QA,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.QA, f"qa:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "render_id": render.id},
    )

    try:
        provider = get_qa_provider()
        reports = provider.run(
            script.id,
            {
                "has_facts": has_facts,
                "segment_count": len(script.segments),
                "voice_ok": generation is not None,
                "assets": [
                    {
                        "id": a.id,
                        "segment_index": a.segment_index,
                        "asset_type": a.asset_type,
                        "commercial_use": a.commercial_use,
                    }
                    for a in assets
                ],
                "reviews": [
                    {
                        "asset_id": r.asset_id,
                        "decision": r.decision,
                        "risk_level": r.risk_level.value,
                    }
                    for r in reviews
                ],
                "subtitle": {
                    "cue_count": subtitle.cue_count,
                    "duration_s": subtitle.duration_s,
                    "format": subtitle.format,
                },
                "render_ok": render.status == RenderStatus.RENDERED,
                "render_duration_s": render.duration_s,
                "render_file_size": render.file_size_bytes,
                "render_resolution": render.resolution,
                "render_fps": render.fps,
                "expected_resolution": settings.render_resolution,
            },
        )
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"QA failed: {e}")

    # Replace QA reports cho script (mỗi lần chạy QA ghi đè kết quả mới nhất).
    db.execute(delete(QAReport).where(QAReport.script_id == script.id))
    for rep in reports:
        db.add(
            QAReport(
                script_id=script.id,
                owner_id=current_user.id,
                gate=rep.gate,
                passed=rep.passed,
                mandatory=rep.mandatory,
                checks=[c.model_dump() for c in rep.checks],
                severity=rep.severity,
                notes=rep.notes,
            )
        )
    final_passed = next((r.passed for r in reports if r.gate == "final"), False)
    script.pipeline_status = "qa"
    db.flush()

    result = QAResult(
        job_id=job.id,
        script_id=script.id,
        reports=reports,
        final_passed=final_passed,
    )
    mark_job_success(db, job, result.model_dump())
    db.commit()

    return result