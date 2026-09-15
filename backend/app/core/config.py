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

    # ---- Phase 4: visual plan / assets / copyright providers ----
    visual_provider: str = "offline"
    asset_provider: str = "offline"
    copyright_provider: str = "offline"
    asset_source_hint: str = "ai_generated"

    # ---- Phase 5: render / subtitle / QA providers ----
    render_provider: str = "offline"
    subtitle_provider: str = "offline"
    qa_provider: str = "offline"
    # Cấu hình render (offline dùng để QA so sánh kỳ vọng).
    render_resolution: str = "1280x720"
    render_fps: int = 30
    render_audio_codec: str = "aac"
    # Thư mục lưu output render (offline chỉ tạo URL placeholder).
    render_output_dir: str = "/data/render"

    # ---- Phase 6: YouTube publishing providers ----
    youtube_provider: str = "offline"
    # Credential cho provider thật (YouTube Data API / OAuth) — bắt buộc đặt trong .env,
    # tuyệt đối không hard-code client secret hoặc access token vào code.
    youtube_client_id: str = ""
    youtube_refresh_token: str = ""

    # ---- Phase 7: analytics / experiments / learning providers ----
    analytics_provider: str = "offline"
    # Provider thật (YouTube Analytics API) sẽ dùng chung credential YouTube ở trên.

    # ---- Phase 8: cost engine (docs/11) ----
    # Mode mặc định khi tạo project (free / balanced / premium) — multiplier scaling.
    cost_mode_default: str = "balanced"
    # Mức cảnh báo khi chi phí đã dùng vượt ngưỡng % của max_cost_per_video.
    cost_alert_threshold_pct: float = 0.8
    # Rate mặc định (USD) — offline darling an toàn; cho phép đè qua env khi có provider thật.
    cost_rate_voice_per_1k_chars: float = 0.0001
    cost_rate_render_per_minute: float = 0.001

    # ---- Phase 8: fallback + retry + circuit breaker ----
    max_retries_default: int = 3
    retry_backoff_base_seconds: float = 2.0
    retry_backoff_max_seconds: float = 60.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 60.0
    request_timeout_seconds: int = 30

    # ---- Phase 8: production hardening / observability ----
    # Redis dùng cho queue/worker + rate limit + cache (Phase 8; chưa bắt buộc khi offline).
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    request_id_header: str = "x-request-id"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()