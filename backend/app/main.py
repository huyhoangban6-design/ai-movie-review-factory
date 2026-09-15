from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.angles import router as angles_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.copyright import router as copyright_router
from app.api.jobs import router as jobs_router
from app.api.middleware import RateLimitMiddleware
from app.api.movies import router as movies_router
from app.api.opportunity import router as opportunity_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.scripts import router as scripts_router
from app.api.timeline import router as timeline_router
from app.api.visual import router as visual_router
from app.api.voice import router as voice_router
from app.api.video import router as video_router
from app.api.youtube import router as youtube_router
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_app_route_paths = tuple(
    f"{settings.api_v1_prefix}{p}"
    for p in ("/auth/register", "/auth/login")
)
app.add_middleware(
    RateLimitMiddleware,
    limit=settings.auth_rate_limit_per_minute,
    window_seconds=settings.auth_rate_limit_window_seconds,
    paths=_app_route_paths,
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(projects_router, prefix=settings.api_v1_prefix)
app.include_router(jobs_router, prefix=settings.api_v1_prefix)
app.include_router(research_router, prefix=settings.api_v1_prefix)
app.include_router(opportunity_router, prefix=settings.api_v1_prefix)
app.include_router(angles_router, prefix=settings.api_v1_prefix)
app.include_router(movies_router, prefix=settings.api_v1_prefix)
app.include_router(scripts_router, prefix=settings.api_v1_prefix)
app.include_router(voice_router, prefix=settings.api_v1_prefix)
app.include_router(timeline_router, prefix=settings.api_v1_prefix)
app.include_router(visual_router, prefix=settings.api_v1_prefix)
app.include_router(assets_router, prefix=settings.api_v1_prefix)
app.include_router(copyright_router, prefix=settings.api_v1_prefix)
app.include_router(video_router, prefix=settings.api_v1_prefix)
app.include_router(youtube_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


_frontend_dist = Path(settings.frontend_dist_path)
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")