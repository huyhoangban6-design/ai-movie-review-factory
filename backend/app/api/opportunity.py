import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.movie import Movie, Opportunity
from app.models.user import User
from app.schemas.api import ScoreRequest, ScoreResult
from app.services.factory import get_opportunity_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key

router = APIRouter(prefix="/opportunities", tags=["opportunity"])


def _load_movie(db: Session, movie_id: int, owner_id: int) -> Movie:
    movie = db.scalar(select(Movie).where(Movie.id == movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("/score", response_model=ScoreResult, status_code=status.HTTP_201_CREATED)
def score_movie(
    payload: ScoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScoreResult:
    movie = _load_movie(db, payload.movie_id, current_user.id)

    key = hashlib.sha256(str(movie.id).encode()).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.OPPORTUNITY_SCORE,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.OPPORTUNITY_SCORE, f"opp:{key}"),
        project_id=movie.project_id,
        input_payload={"movie_id": movie.id},
    )

    try:
        provider = get_opportunity_provider()
        score = provider.score(movie)
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Opportunity scoring failed: {e}")

    opp = db.scalar(select(Opportunity).where(Opportunity.movie_id == movie.id))
    data = score.model_dump()
    if opp is None:
        opp = Opportunity(movie_id=movie.id)
        db.add(opp)
    opp.overall_score = data["overall"]
    opp.sub_scores = data
    opp.confidence = data["confidence"]
    opp.rationale = data["rationale"]
    db.flush()
    opp_id = opp.id

    mark_job_success(db, job, score.model_dump())
    db.commit()

    return ScoreResult(job_id=job.id, opportunity_id=opp_id, movie_id=movie.id, score=score)