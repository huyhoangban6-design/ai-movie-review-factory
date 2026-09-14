from typing import Optional

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseORM


class MediaSource(BaseORM):
    __tablename__ = "media_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    commercial_use: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    usage_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)