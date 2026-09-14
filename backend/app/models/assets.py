import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseORM


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Asset(BaseORM):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    commercial_use: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acquisition_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    usage_context: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transformations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sources: Mapped[list["AssetSource"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["CopyrightReview"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class AssetSource(BaseORM):
    __tablename__ = "asset_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship(back_populates="sources")  # pyright: ignore


class CopyrightReview(BaseORM):
    __tablename__ = "copyright_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, native_enum=False, length=16), nullable=False
    )
    duration_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_notes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    decision: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship(back_populates="reviews")  # pyright: ignore