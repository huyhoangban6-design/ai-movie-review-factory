from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import Job, JobStatus, JobType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_job(
    db: Session,
    owner_id: int,
    job_type: JobType,
    idempotency_key: str,
    project_id: int | None = None,
    input_payload: dict[str, Any] | None = None,
) -> Job:
    job = Job(
        project_id=project_id,
        owner_id=owner_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        idempotency_key=idempotency_key,
        input_payload=json.dumps(input_payload, ensure_ascii=False) if input_payload else None,
        max_retries=settings.max_retries_default,
        completed_at=None,
    )
    db.add(job)
    db.flush()
    return job


def next_attempt_key(db: Session, owner_id: int, job_type: JobType, base: str) -> str:
    """Ghép base key với số lần chạy trước để idempotency key luôn unique cho các
    thao tác chạy lại được (script v2, asset replace, render lại…)."""
    attempts = db.scalar(
        select(func.count(Job.id)).where(
            Job.owner_id == owner_id,
            Job.job_type == job_type,
            Job.idempotency_key.like(f"{owner_id}:{base}:%"),
        )
    ) or 0
    return f"{owner_id}:{base}:{attempts + 1}"


def mark_job_success(db: Session, job: Job, output: Any) -> Job:
    job.status = JobStatus.SUCCEEDED
    job.output_summary = (
        output.model_dump_json() if hasattr(output, "model_dump_json") else json.dumps(output, ensure_ascii=False)
    )
    job.completed_at = _utcnow()
    db.flush()
    return job


def mark_job_failed(db: Session, job: Job, message: str) -> Job:
    job.status = JobStatus.FAILED
    job.error_message = message[:5000]
    job.completed_at = _utcnow()
    db.flush()
    return job


def mark_job_running(db: Session, job: Job) -> Job:
    job.status = JobStatus.RUNNING
    job.started_at = job.started_at or _utcnow()
    db.flush()
    return job


def mark_job_retry_pending(db: Session, job: Job) -> Job:
    """Set the job back to PENDING with next_retry_at = now + exponential backoff."""
    job.status = JobStatus.PENDING
    job.retry_count = (job.retry_count or 0) + 1
    job.error_message = None
    delay = get_retry_delay(job)
    job.next_retry_at = _utcnow() + timedelta(seconds=delay)
    db.flush()
    return job


def should_retry(job: Job) -> bool:
    """A FAILED job can be retried automatically if retries under the cap."""
    max_retries = job.max_retries if job.max_retries is not None else settings.max_retries_default
    return job.status == JobStatus.FAILED and (job.retry_count or 0) < max_retries


def get_retry_delay(job: Job, attempt: int | None = None) -> float:
    """Exponential backoff delay for the job's next retry (capped)."""
    attempt = (job.retry_count or 0) if attempt is None else attempt
    base = settings.retry_backoff_base_seconds
    cap = settings.retry_backoff_max_seconds
    return min(base * (2 ** max(attempt - 1, 0)), cap)