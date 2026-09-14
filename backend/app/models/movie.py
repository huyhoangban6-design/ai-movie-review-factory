from typing import Optional

from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseORM


class Movie(BaseORM):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    director: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    synopsis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    poster_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    release_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    sources: Mapped[list["MovieSource"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["MovieAnalysis"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", uselist=False
    )
    angles: Mapped[list["ContentAngle"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", order_by="ContentAngle.id"
    )


class MovieSource(BaseORM):
    __tablename__ = "movie_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    movie: Mapped["Movie"] = relationship(back_populates="sources")  # pyright: ignore


class MovieAnalysis(BaseORM):
    __tablename__ = "movies_analysis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    facts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    themes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    movie: Mapped["Movie"] = relationship(back_populates="analyses")  # pyright: ignore


class Opportunity(BaseORM):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sub_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    strategy_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    movie: Mapped["Movie"] = relationship(back_populates="opportunity")  # pyright: ignore


class ContentAngle(BaseORM):
    __tablename__ = "content_angles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    angle_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hook: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    movie: Mapped["Movie"] = relationship(back_populates="angles")  # pyright: ignore


class Competitor(BaseORM):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    influence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top_videos: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    movie: Mapped["Movie"] = relationship()  # pyright: ignore


class CompetitorVideo(BaseORM):
    __tablename__ = "competitor_videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    movie_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    influence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retrieval_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    competitor: Mapped["Competitor"] = relationship()  # pyright: ignore