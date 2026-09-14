import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.movie import Movie
from app.models.scripting import Script, ScriptTimeline, VoiceGeneration
from app.models.user import User
from app.schemas.api import TimelineRequest, TimelineResult
from app.schemas.scripting import SentenceTimestamp
from app.services.factory import get_timeline_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key

router = APIRouter(prefix="/timeline", tags=["timeline"])


def _load_script(db: Session, script_id: int, owner_id: int) -> tuple[Script, int | None]:
    script = db.scalar(select(Script).where(Script.id == script_id))
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    movie = db.scalar(select(Movie).where(Movie.id == script.movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script, movie.project_id


def _load_generation(db: Session, generation_id: int, script_id: int) -> VoiceGeneration:
    generation = db.scalar(
        select(VoiceGeneration).where(
            VoiceGeneration.id == generation_id, VoiceGeneration.script_id == script_id
        )
    )
    if generation is None:
        raise HTTPException(status_code=404, detail="Voice generation not found for this script")
    return generation


@router.post("/build", response_model=TimelineResult, status_code=status.HTTP_201_CREATED)
def build_timeline(
    payload: TimelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimelineResult:
    script, project_id = _load_script(db, payload.script_id, current_user.id)

    if payload.generation_id is not None:
        generation = _load_generation(db, payload.generation_id, script.id)
    else:
        generation = db.scalar(
            select(VoiceGeneration)
            .where(VoiceGeneration.script_id == script.id, VoiceGeneration.status == "completed")
            .order_by(VoiceGeneration.id.desc())
        )

    if generation is None:
        raise HTTPException(
            status_code=422,
            detail="Chưa có bản voice nào cho script này. Chạy POST /voice/generate trước.",
        )

    key = hashlib.sha256(f"{script.id}|{generation.id}".encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.TIMELINE,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.TIMELINE, f"timeline:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "generation_id": generation.id},
    )

    segments = sorted(script.segments, key=lambda s: s.position)
    full_text = "\n".join(s.text for s in segments)
    segment_texts = [s.text for s in segments]
    sentences = [
        SentenceTimestamp(sentence=s["sentence"], start_s=s["start_s"], end_s=s["end_s"])
        for s in (generation.sentences or [])
    ]

    try:
        provider = get_timeline_provider()
        output = provider.build(full_text, segment_texts, sentences)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Timeline build failed: {e}")

    db.execute(delete(ScriptTimeline).where(ScriptTimeline.script_id == script.id))
    timeline = ScriptTimeline(
        script_id=script.id,
        generation_id=generation.id,
        total_duration_s=output.total_duration_s,
        segments=[s.model_dump() for s in output.segments],
    )
    db.add(timeline)
    db.flush()
    timeline_id = timeline.id

    mark_job_success(db, job, output.model_dump())
    db.commit()

    return TimelineResult(
        job_id=job.id,
        timeline_id=timeline_id,
        script_id=script.id,
        generation_id=generation.id,
        timeline=output,
    )