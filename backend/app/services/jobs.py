from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType


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
    )
    db.add(job)
    db.flush()
    return job


def mark_job_success(db: Session, job: Job, output: Any) -> Job:
    job.status = JobStatus.SUCCEEDED
    job.output_summary = (
        output.model_dump_json() if hasattr(output, "model_dump_json") else json.dumps(output, ensure_ascii=False)
    )
    db.flush()
    return job


def mark_job_failed(db: Session, job: Job, message: str) -> Job:
    job.status = JobStatus.FAILED
    job.error_message = message[:5000]
    db.flush()
    return job