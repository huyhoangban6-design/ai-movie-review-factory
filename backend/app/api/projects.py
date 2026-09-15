from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_idempotency_key
from app.core.database import get_db
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.schemas.api import JobOut, ProjectCreate, ProjectDetail, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int = 50
) -> list[Project]:
    limit = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(Project)
            .where(Project.owner_id == current_user.id)
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> Project:
    client_key = idempotency_key or f"client:{current_user.id}:{uuid4()}"
    scope = f"{current_user.id}:{client_key}"
    existing = db.scalar(
        select(Project).where(Project.idempotency_key == scope, Project.owner_id == current_user.id)
    )
    if existing is not None:
        return existing

    project = Project(
        owner_id=current_user.id,
        idempotency_key=scope,
        title=payload.title,
        description=payload.description,
        max_cost_per_video=payload.max_cost_per_video,
        cost_mode=payload.cost_mode,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _get_owned_project(db: Session, project_id: int, owner_id: int) -> Project:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == owner_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ProjectDetail:
    project = _get_owned_project(db, project_id, current_user.id)
    project.jobs = list(
        db.scalars(
            select(Job)
            .where(Job.project_id == project_id, Job.owner_id == current_user.id)
            .order_by(Job.id.desc())
        )
    )
    return project


@router.get("/{project_id}/jobs", response_model=list[JobOut])
def list_project_jobs(
    project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Job]:
    _get_owned_project(db, project_id, current_user.id)
    return list(
        db.scalars(
            select(Job)
            .where(Job.project_id == project_id, Job.owner_id == current_user.id)
            .order_by(Job.id.desc())
        )
    )