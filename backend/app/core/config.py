from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Movie Review Factory"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./data/app.db"
    secret_key: str = "dev-only-secret-do-not-use-in-production"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"
    token_type: str = "bearer"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    frontend_dist_path: str = "frontend/dist"

    # Rate limit auth endpoints (in-memory; Phase 8 sẽ chuyển lên Redis).
    auth_rate_limit_per_minute: int = 30
    auth_rate_limit_window_seconds: int = 60

    # ---- Phase 2: providers (interface/adapters) ----
    # Mặc định "offline" = provider giả, không gọi network. Chuyển sang provider
    # thật khi có key (bắt buộc config, tuyệt đối không hard-code key).
    research_provider: str = "offline"
    opportunity_provider: str = "offline"
    angle_provider: str = "offline"
    # Key cho provider thật (tùy chọn trong Phase 2; TMDB dùng định dạng API v3).
    tmdb_api_key: str = ""

    # ---- Phase 3: script / voice / timeline providers ----
    script_provider: str = "offline"
    voice_provider: str = "offline"
    timeline_provider: str = "offline"
    # Voice profile mặc định khi /voice/generate không truyền voice_profile_id.
    default_voice_provider: str = "offline"
    default_voice_model: str = "offline-vi-female"
    default_voice_id: str = "offline-vi-female-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()