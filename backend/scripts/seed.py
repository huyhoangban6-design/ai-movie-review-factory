"""Tạo user + project mẫu cho dev local. Usage:
    cd backend && python scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.job import Job, JobStatus, JobType  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo = db.query(User).filter(User.email == "demo@example.com").first()
        if demo is None:
            demo = User(
                email="demo@example.com",
                display_name="Demo Creator",
                hashed_password=hash_password("demo-password-123"),
            )
            db.add(demo)
            db.flush()
            print("Created demo user: demo@example.com / demo-password-123")
        else:
            print("Demo user already exists.")

        if not db.query(Project).filter(Project.owner_id == demo.id).first():
            project = Project(owner_id=demo.id, title="Demo: Inception Review", description="Sample project")
            db.add(project)
            db.flush()
            db.add(
                Job(
                    project_id=project.id,
                    owner_id=demo.id,
                    job_type=JobType.MOVIE_RESEARCH,
                    status=JobStatus.PENDING,
                    idempotency_key=f"seed:{demo.id}:{project.id}",
                )
            )
            print("Created demo project + kickoff job.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()