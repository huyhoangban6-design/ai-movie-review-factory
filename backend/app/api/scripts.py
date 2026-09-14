import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.movie import ContentAngle, Movie
from app.models.scripting import Script, ScriptSegment, ScriptTimeline, VoiceGeneration
from app.models.user import User
from app.schemas.api import ScriptRequest, ScriptResult
from app.schemas.scripting import (
    GenerationOut,
    ScriptDetailOut,
    SegmentDetailOut,
    TimelineOut,
)
from app.services.factory import get_script_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success

router = APIRouter(prefix="/scripts", tags=["scripts"])


def _load_movie(db: Session, movie_id: int, owner_id: int) -> Movie:
    movie = db.scalar(select(Movie).where(Movie.id == movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


def _load_script(db: Session, script_id: int, owner_id: int) -> Script:
    script = db.scalar(select(Script).where(Script.id == script_id))
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    movie = db.scalar(select(Movie).where(Movie.id == script.movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


def _load_angle(db: Session, movie_id: int, angle_id: int) -> ContentAngle:
    angle = db.scalar(
        select(ContentAngle).where(ContentAngle.id == angle_id, ContentAngle.movie_id == movie_id)
    )
    if angle is None:
        raise HTTPException(status_code=404, detail="Angle not found for this movie")
    return angle


@router.post("/generate", response_model=ScriptResult, status_code=status.HTTP_201_CREATED)
def generate_script(
    payload: ScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScriptResult:
    movie = _load_movie(db, payload.movie_id, current_user.id)

    angle = None
    if payload.angle_id is not None:
        angle = _load_angle(db, movie.id, payload.angle_id)
    else:
        angle = db.scalar(
            select(ContentAngle)
            .where(ContentAngle.movie_id == movie.id, ContentAngle.status == "active")
            .order_by(ContentAngle.id)
        )

    key = hashlib.sha256(f"{movie.id}|{payload.angle_id}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.SCRIPT,
        idempotency_key=f"{current_user.id}:script:{key}",
        project_id=movie.project_id,
        input_payload={"movie_id": movie.id, "angle_id": payload.angle_id},
    )

    try:
        provider = get_script_provider()
        output = provider.generate(movie, angle)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Script generation failed: {e}")

    max_version = db.scalar(select(func.max(Script.version)).where(Script.movie_id == movie.id)) or 0
    script = Script(
        movie_id=movie.id,
        angle_id=angle.id if angle else None,
        version=max_version + 1,
        title=output.title,
        word_count=output.word_count,
        estimated_duration_s=output.estimated_duration_s,
    )
    db.add(script)
    db.flush()
    for i, seg in enumerate(output.segments, start=1):
        db.add(
            ScriptSegment(
                script_id=script.id,
                position=i,
                section=seg.section.value,
                text=seg.text,
                duration_estimate_s=round(len(seg.text) / 12.0, 2),
            )
        )

    mark_job_success(db, job, output.model_dump())
    db.commit()

    return ScriptResult(
        job_id=job.id,
        script_id=script.id,
        movie_id=movie.id,
        angle_id=script.angle_id,
        version=script.version,
        script=output,
    )


@router.get("/{script_id}", response_model=ScriptDetailOut)
def get_script_detail(
    script_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ScriptDetailOut:
    script = _load_script(db, script_id, current_user.id)

    segments = [
        SegmentDetailOut.model_validate(s, from_attributes=True)
        for s in sorted(script.segments, key=lambda x: x.position)
    ]
    generation = db.scalar(
        select(VoiceGeneration)
        .where(VoiceGeneration.script_id == script.id, VoiceGeneration.status == "completed")
        .order_by(VoiceGeneration.id.desc())
    )
    timeline = db.scalar(
        select(ScriptTimeline)
        .where(ScriptTimeline.script_id == script.id)
        .order_by(ScriptTimeline.id.desc())
    )

    return ScriptDetailOut(
        id=script.id,
        movie_id=script.movie_id,
        angle_id=script.angle_id,
        version=script.version,
        status=script.status.value,
        title=script.title,
        word_count=script.word_count,
        estimated_duration_s=script.estimated_duration_s,
        created_at=script.created_at,
        segments=segments,
        latest_generation=(
            GenerationOut.model_validate(generation, from_attributes=True)
            if generation
            else None
        ),
        timeline=TimelineOut.model_validate(timeline, from_attributes=True) if timeline else None,
    )