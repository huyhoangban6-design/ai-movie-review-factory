import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.job import JobType
from app.models.movie import Movie
from app.models.scripting import (
    CommercialUse,
    Script,
    VoiceGeneration,
    VoiceProfile,
)
from app.models.user import User
from app.schemas.api import VoiceRequest, VoiceResult
from app.services.cost import check_budget, record_job_cost
from app.services.factory import get_voice_provider
from app.services.fallback import ProviderUnavailableError, run_with_fallback
from app.services.jobs import create_job, mark_job_failed, mark_job_success, next_attempt_key
from app.services.providers import OfflineVoiceProvider

router = APIRouter(prefix="/voice", tags=["voice"])

DEFAULT_PROFILE_NAME = "Mặc định offline"


def _load_script(db: Session, script_id: int, owner_id: int) -> tuple[Script, int | None]:
    script = db.scalar(select(Script).where(Script.id == script_id))
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    movie = db.scalar(select(Movie).where(Movie.id == script.movie_id, Movie.owner_id == owner_id))
    if movie is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script, movie.project_id


def _get_or_create_default_profile(db: Session, owner_id: int) -> VoiceProfile:
    profile = db.scalar(
        select(VoiceProfile)
        .where(
            VoiceProfile.owner_id == owner_id,
            VoiceProfile.name == DEFAULT_PROFILE_NAME,
            VoiceProfile.status == "active",
        )
        .order_by(VoiceProfile.id)
    )
    if profile is None:
        profile = db.scalar(
            select(VoiceProfile)
            .where(
                VoiceProfile.owner_id == owner_id,
                VoiceProfile.commercial_use == CommercialUse.YES,
                VoiceProfile.status == "active",
            )
            .order_by(VoiceProfile.id)
        )
    if profile is not None:
        return profile
    profile = VoiceProfile(
        owner_id=owner_id,
        name=DEFAULT_PROFILE_NAME,
        voice_id=settings.default_voice_id,
        provider=settings.default_voice_provider,
        model=settings.default_voice_model,
        language="vi",
        style="documentary",
        speed=1.0,
        emotion="neutral",
        commercial_use=CommercialUse.YES,
        license_url="https://example.com/license/offline",
        cloning_permission=False,
    )
    db.add(profile)
    db.flush()
    return profile


def _load_profile(db: Session, profile_id: int, owner_id: int) -> VoiceProfile:
    profile = db.scalar(
        select(VoiceProfile).where(VoiceProfile.id == profile_id, VoiceProfile.owner_id == owner_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return profile


@router.post("/generate", response_model=VoiceResult, status_code=status.HTTP_201_CREATED)
def generate_voice(
    payload: VoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoiceResult:
    script, project_id = _load_script(db, payload.script_id, current_user.id)

    if payload.voice_profile_id is not None:
        profile = _load_profile(db, payload.voice_profile_id, current_user.id)
    else:
        profile = _get_or_create_default_profile(db, current_user.id)
    db.flush()

    speed = payload.speed if payload.speed is not None else profile.speed
    if not (0.5 <= speed <= 2.0):
        raise HTTPException(status_code=422, detail="speed must be between 0.5 and 2.0")

    if profile.commercial_use == CommercialUse.NO:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Voice '{profile.name}' cấm dùng thương mại (license gate). "
                "Chọn voice khác có commercial_use=yes."
            ),
        )

    text = "\n".join(seg.text for seg in script.segments)

    # Phase 8 cost engine (docs/11): pre-job estimate + budget gate (402 khi vượt).
    check_budget(
        db,
        project_id,
        units=float(len(text)),
        job_type=JobType.VOICE,
        provider=profile.provider,
    )

    key = hashlib.sha256(
        f"{script.id}|{profile.id}|{speed}".encode()
    ).hexdigest()[:24]
    job = create_job(
        db,
        current_user.id,
        JobType.VOICE,
        idempotency_key=next_attempt_key(db, current_user.id, JobType.VOICE, f"voice:{key}"),
        project_id=project_id,
        input_payload={"script_id": script.id, "voice_profile_id": profile.id, "speed": speed},
    )

    def _synthesize(provider):
        return provider.synthesize(
            text,
            provider=profile.provider,
            model=profile.model,
            voice_id=profile.voice_id,
            language=profile.language,
            speed=speed,
            commercial_use=profile.commercial_use.value,
            license_url=profile.license_url,
            cloning_permission=profile.cloning_permission,
        )

    try:
        # Phase 8 fallback (docs/11): primary retry + backoff, fallback offline provider.
        output = run_with_fallback(
            lambda: _synthesize(get_voice_provider()),
            fallbacks=(lambda: _synthesize(OfflineVoiceProvider()),),
            provider_name="voice",
            max_retries=2,
            sleep=lambda _: None,
        )
    except ProviderUnavailableError as exc:
        mark_job_failed(db, job, str(exc))
        db.commit()
        raise HTTPException(status_code=503, detail=f"Voice provider unavailable: {exc}") from exc
    except Exception as e:  # noqa: BLE001
        mark_job_failed(db, job, str(e))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {e}")

    text_hash = hashlib.sha256(f"{text}|{profile.provider}|{profile.model}|{profile.voice_id}|{speed}".encode()).hexdigest()
    generation = VoiceGeneration(
        script_id=script.id,
        voice_profile_id=profile.id,
        owner_id=current_user.id,
        status="completed",
        text_hash=text_hash,
        audio_url=output.audio_url,
        audio_duration_s=output.duration_s,
        provider=output.provider,
        model=output.model,
        voice_id=output.voice_id,
        language=output.language,
        speed=output.speed,
        words=[w.model_dump() for w in output.words],
        sentences=[s.model_dump() for s in output.sentences],
        license_info=output.license.model_dump(),
        cost=0.0,
    )
    db.add(generation)
    db.flush()
    gen_id = generation.id

    mark_job_success(db, job, output.model_dump())
    record_job_cost(db, job, provider=output.provider or "offline", model=output.model, units=float(len(text)))
    db.commit()

    return VoiceResult(
        job_id=job.id,
        generation_id=gen_id,
        script_id=script.id,
        voice_profile_id=profile.id,
        voice=output,
    )