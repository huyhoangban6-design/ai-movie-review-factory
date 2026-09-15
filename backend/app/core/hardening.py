"""Production-hardening config validation + runtime checks (Phase 8).

Startup validation refuses to silently run "offline" when a real provider was
requested but its credential is missing — instead of failing at request time.
"""

from __future__ import annotations

import logging

from app.core.config import settings

log = logging.getLogger("app.hardening")

# mapping provider: (provider_setting_name, required_credential_settings)
_REQUIRED_CREDENTIALS: dict[str, tuple[str, ...]] = {
    "research_provider": ("tmdb_api_key",),     # real research uses TMDB
    "youtube_provider": ("youtube_client_id", "youtube_refresh_token"),
    "analytics_provider": ("youtube_client_id", "youtube_refresh_token"),
}

# settings that have no real adapter yet: only "offline" is safe.
_NOT_IMPLEMENTED: set[str] = {
    "opportunity_provider",
    "angle_provider",
    "script_provider",
    "voice_provider",
    "timeline_provider",
    "visual_provider",
    "asset_provider",
    "copyright_provider",
    "render_provider",
    "subtitle_provider",
    "qa_provider",
}


def validate_runtime_config() -> list[str]:
    """Check environment wiring; returns list of problems (empty when all safe).

    Non-fatal at startup: logs errors prominently so operator fixes .env before
    real traffic. Any non-offline provider without credential -> problem.
    """
    problems: list[str] = []
    current = settings.model_dump()

    for setting_name, creds in _REQUIRED_CREDENTIALS.items():
        provider = current.get(setting_name, "offline").lower()
        if provider == "offline":
            continue
        missing = [c for c in creds if not current.get(c)]
        if missing:
            problems.append(
                f"{setting_name}='{provider}' requires env credential(s) {missing} — "
                "bắt buộc đặt trong .env (tuyệt đối không hard-code key)."
            )

    for setting_name in _NOT_IMPLEMENTED:
        provider = current.get(setting_name, "offline").lower()
        if provider != "offline":
            problems.append(
                f"{setting_name}='{provider}' not available yet — only 'offline' supported."
            )

    if settings.cost_mode_default not in ("free", "balanced", "premium"):
        problems.append(
            f"COST_MODE_DEFAULT='{settings.cost_mode_default}' invalid "
            "(must be free|balanced|premium)."
        )

    if settings.cost_alert_threshold_pct <= 0 or settings.cost_alert_threshold_pct > 1:
        problems.append("COST_ALERT_THRESHOLD_PCT must be in (0, 1].")

    if settings.max_retries_default < 0:
        problems.append("MAX_RETRIES_DEFAULT must be >= 0.")

    if settings.circuit_breaker_threshold < 1:
        problems.append("CIRCUIT_BREAKER_THRESHOLD must be >= 1.")

    if not settings.secret_key or settings.secret_key == "dev-only-secret-do-not-use-in-production":
        problems.append(
            "SECRET_KEY is the dev default — set a strong random secret in production."
        )

    return problems


def warn_on_runtime_problems() -> None:
    for problem in validate_runtime_config():
        log.error("CONFIG: %s", problem)
    if not settings.secret_key or settings.secret_key == "dev-only-secret-do-not-use-in-production":
        log.warning("CONFIG: SECRET_KEY dev default detected — secure before production.")