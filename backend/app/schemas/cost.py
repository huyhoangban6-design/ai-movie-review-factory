from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.cost import CostRecordStatus


class CostEstimateRequest(BaseModel):
    job_type: str = Field(..., min_length=1, max_length=32)
    units: float = Field(default=1.0, ge=0.0, le=1e9)
    provider: str = Field(default="offline", max_length=64)
    model: str | None = Field(default=None, max_length=128)
    mode: str = Field(default="balanced", pattern="^(free|balanced|premium)$")


class CostEstimateOut(BaseModel):
    job_type: str
    provider: str
    model: str | None
    mode: str
    unit: str
    units: float
    unit_rate_usd: float
    estimated_cost_usd: float
    category: str
    currency: str = "usd"


class CostRecordOut(BaseModel):
    id: int
    job_id: int | None
    project_id: int | None
    job_type: str
    provider: str
    model: str | None
    mode: str
    category: str
    unit: str
    units: float
    unit_rate_usd: float
    estimated_cost_usd: float
    actual_cost_usd: float
    currency: str
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CostRecordCreate(BaseModel):
    project_id: int | None = None
    job_id: int | None = None
    job_type: str = Field(..., min_length=1, max_length=32)
    provider: str = Field(default="offline", max_length=64)
    model: str | None = Field(default=None, max_length=128)
    mode: str = Field(default="balanced", pattern="^(free|balanced|premium)$")
    category: str = Field(default="other", max_length=32)
    unit: str = Field(default="job", max_length=16)
    units: float = Field(default=1.0, ge=0.0, le=1e12)
    unit_rate_usd: float = Field(default=0.0, ge=0.0, le=1e9)
    actual_cost_usd: float = Field(..., ge=0.0, le=1e9)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0, le=1e9)
    status: str = Field(default=CostRecordStatus.RECORDED.value, max_length=16)
    notes: str | None = Field(default=None, max_length=500)


class ProjectBudgetUpdate(BaseModel):
    max_cost_per_video: float | None = Field(default=None, gt=0.0, le=1_000_000)
    cost_mode: str | None = Field(default=None, pattern="^(free|balanced|premium)$")


class ProjectCostSummaryOut(BaseModel):
    project_id: int
    title: str
    cost_mode: str
    max_cost_per_video: float | None
    total_estimated_usd: float
    total_actual_usd: float
    remaining_budget: float | None
    budget_percent_used: float | None
    per_category: dict[str, float]
    per_provider: dict[str, float]
    alerts: list[str]
    records: list[CostRecordOut]


class CostAlertOut(BaseModel):
    id: int
    level: str
    message: str
    details: dict[str, Any] | None
    occurred_at: datetime | None