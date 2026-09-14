import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.movie import ContentAngle, Movie
from app.models.user import User
from app.schemas.api import AnglesResult, ScoreRequest
from app.schemas.research import Angle
from app.services.factory import get_angle_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key

router = APIRouter(prefix="/content/angles", tags=["angles"])


def _load_movie(db: Session, movie_id: int, owner_id: int) -> Movie:
    movie = db.scalar(select(Movie).where(Movie.id == movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("", response_model=AnglesResult, status_code=status.HTTP_201_CREATED)
def generate_angles(
    payload: ScoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnglesResult:
    movie = _load_movie(db, payload.movie_id, current_user.id)

    key = hashlib.sha256(str(movie.id).encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.CONTENT_ANGLE,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.CONTENT_ANGLE, f"angles:{key}"),
        project_id=movie.project_id,
        input_payload={"movie_id": movie.id},
    )

    try:
        provider = get_angle_provider()
        output = provider.angles(movie)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Angle generation failed: {e}")

    db.execute(delete(ContentAngle).where(ContentAngle.movie_id == movie.id))
    created: list[Angle] = []
    for a in output.angles:
        db.add(
            ContentAngle(
                movie_id=movie.id,
                angle_type=a.angle_type,
                title=a.title,
                summary=a.summary,
                hook=a.hook,
                rationale=a.rationale,
            )
        )
        created.append(a)

    mark_job_success(db, job, output.model_dump())
    db.commit()

    return AnglesResult(job_id=job.id, movie_id=movie.id, angles=created)