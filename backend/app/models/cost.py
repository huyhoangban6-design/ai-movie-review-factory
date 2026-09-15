import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseORM


class CostMode(str, enum.Enum):
    FREE = "free"          # tối thiểu chi phí (multiplier thấp)
    BALANCED = "balanced"  # cân bằng chất lượng / chi phí
    PREMIUM = "premium"    # chất lượng tối đa


class CostRecordStatus(str, enum.Enum):
    ESTIMATED = "estimated"  # ước tính trước job
    RECORDED = "recorded"    # ghi nhận thực tế sau job
    ADJUSTED = "adjusted"    # điều chỉnh thủ công (hoá đơn thật)


class CostRecord(BaseORM):
    """Bảng cost engine (docs/03) — mỗi hàng là một khoản chi phí provider/model/job.

    Estimated (pre-job) và actual (post-job) đều ghi vào đây; offline provider
    deterministic nên actual == estimated. Docs/11: record actual cost theo
    provider/model/job.
    """

    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default=CostMode.BALANCED.value, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    units: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unit_rate_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=CostRecordStatus.RECORDED.value, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SystemLog(BaseORM):
    """Bảng hệ thống (docs/03) — structured log cho observability, cost alerts,
    provider failures. Logger Python vẫn hoạt động song song; bảng này cho các
    sự kiện quan trọng cần truy vấn lại."""

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    logger: Mapped[str] = mapped_column(String(64), default="app", nullable=False)
    event: Mapped[str] = mapped_column(String(64), default="log", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=True
    )

    def __str__(self) -> str:  # pragma: no cover
        return f"<SystemLog {self.level} {self.event}: {self.message[:60]}>"


__all__ = ["CostMode", "CostRecord", "CostRecordStatus", "SystemLog"]