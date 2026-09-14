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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()