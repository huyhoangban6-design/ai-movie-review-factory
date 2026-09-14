from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")

if IS_SQLITE:
    _db_path = settings.database_url.split("///", 1)[-1]
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    _connect_args = {"check_same_thread": False}
    engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()