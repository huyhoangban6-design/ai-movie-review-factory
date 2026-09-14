import hashlib

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job, JobType
from app.models.movie import Movie, MovieAnalysis, MovieSource
from app.models.user import User
from app.schemas.api import ResearchJob, ResearchRequest, ResearchResult
from app.services.factory import get_research_provider
from app.services.jobs import create_job, mark_job_failed, mark_job_success

router = APIRouter(prefix="/movies", tags=["research"])


@router.post(
    "/research",
    response_model=ResearchResult,
    status_code=status.HTTP_201_CREATED,
)
def research_movie(
    payload: ResearchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchResult:
    project_id = request.headers.get("X-Project-Id")
    provider = get_research_provider()
    output = provider.research(payload.title, payload.year, payload.genres)

    key = hashlib.sha256(payload.title.strip().lower().encode()).hexdigest()[:32]
    job = create_job(
        db,
        current_user.id,
        JobType.MOVIE_RESEARCH,
        idempotency_key=f"{current_user.id}:research:{key}",
        input_payload=payload.model_dump(),
    )

    movie = Movie(
        owner_id=current_user.id,
        project_id=int(project_id) if project_id and project_id.isdigit() else None,
        title=output.title,
        year=output.year,
        director=output.director,
        genres=output.genres,
        synopsis=output.synopsis,
        poster_url=output.poster_url,
        release_date=output.release_date,
        imdb_id=output.imdb_id,
        tmdb_id=output.tmdb_id,
    )
    db.add(movie)

    if output.summary or output.facts or output.themes:
        db.add(
            MovieAnalysis(
                movie=movie,
                summary=output.summary,
                facts=output.facts or None,
                themes=output.themes or None,
            )
        )
    for s in output.sources:
        db.add(MovieSource(movie=movie, **s.model_dump()))

    try:
        mark_job_success(db, job, dict(payload=payload.model_dump(), output=output.model_dump()))
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))

    db.commit()

    # job vẫn có mốc idempotency riêng cho worker async sau này.
    return ResearchResult(
        movie_id=movie.id,
        title=movie.title,
        year=movie.year,
        genres=movie.genres or [],
        output=output,
    )