from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.movie import Movie
from app.models.scripting import Script


def load_script_for_owner(db: Session, script_id: int, owner_id: int) -> tuple[Script, int | None]:
    """Load script + project_id khi user sở hữu movie của script."""
    script = db.scalar(select(Script).where(Script.id == script_id))
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    movie = db.scalar(select(Movie).where(Movie.id == script.movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script, movie.project_id