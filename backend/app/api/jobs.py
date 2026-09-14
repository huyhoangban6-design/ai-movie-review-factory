from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.api import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == current_user.id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job