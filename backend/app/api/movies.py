from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.movie import ContentAngle, Movie, MovieAnalysis, MovieSource, Opportunity
from app.models.scripting import Script
from app.models.user import User
from app.schemas.movie import MovieDetailOut, OpportunityOut, SourceOut
from app.schemas.research import Angle
from app.schemas.scripting import ScriptSummaryOut

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/{movie_id}", response_model=MovieDetailOut)
def get_movie_detail(
    movie_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> MovieDetailOut:
    movie = db.scalar(select(Movie).where(Movie.id == movie_id, Movie.owner_id == current_user.id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    sources = list(db.scalars(select(MovieSource).where(MovieSource.movie_id == movie.id)))
    analyses = list(db.scalars(select(MovieAnalysis).where(MovieAnalysis.movie_id == movie.id)))
    opp = db.scalar(select(Opportunity).where(Opportunity.movie_id == movie.id))
    angles = list(
        db.scalars(
            select(ContentAngle).where(ContentAngle.movie_id == movie.id).order_by(ContentAngle.id)
        )
    )
    scripts = list(
        db.scalars(select(Script).where(Script.movie_id == movie.id).order_by(Script.id.desc()))
    )

    summaries = [a.summary for a in analyses if a.summary]
    facts: list[str] = []
    for a in analyses:
        if a.facts:
            facts.extend(str(f) for f in a.facts)

    return MovieDetailOut(
        id=movie.id,
        owner_id=movie.owner_id,
        project_id=movie.project_id,
        title=movie.title,
        year=movie.year,
        director=movie.director,
        genres=movie.genres or [],
        synopsis=movie.synopsis,
        poster_url=movie.poster_url,
        imdb_id=movie.imdb_id,
        tmdb_id=movie.tmdb_id,
        status="verified",
        created_at=movie.created_at,
        sources=[
            SourceOut(
                id=s.id,
                source_type=s.source_type,
                source_url=s.source_url,
                title=s.title,
                publisher=s.publisher,
                published_at=s.published_at,
                summary=s.summary,
                provenance=s.provenance,
            )
            for s in sources
        ],
        summaries=summaries,
        opportunity=OpportunityOut(
            id=opp.id,
            overall=float(opp.overall_score) if opp.overall_score is not None else None,
            sub_scores=opp.sub_scores,
            confidence=float(opp.confidence) if opp.confidence is not None else None,
            rationale=opp.rationale,
            created_at=opp.created_at,
        )
        if opp
        else None,
        angles=[
            Angle(
                angle_type=a.angle_type or "unknown",
                title=a.title,
                summary=a.summary or "",
                hook=a.hook or "",
                rationale=a.rationale or "",
            )
            for a in angles
        ],
        facts=facts,
        scripts=[ScriptSummaryOut.model_validate(s, from_attributes=True) for s in scripts],
    )