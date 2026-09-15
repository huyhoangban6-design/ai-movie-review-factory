"""Provider fallback + circuit breaker + retry with backoff (Phase 8).

In-memory circuit registry: after N consecutive failures a provider circuit
opens; callers get ProviderUnavailableError (→ HTTP 503) until reset window
passes. `run_with_fallback` retries the primary then tries fallback providers;
`sleep` is injectable so tests run without waiting.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from app.core.config import settings

log = logging.getLogger("app.fallback")

T = TypeVar("T")


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider is down / circuit is open."""


# in-memory circuit registry: provider_name -> {"failures", "opened_at", "state"}
_CIRCUITS: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def circuit_status(provider_name: str) -> dict[str, Any]:
    c = _CIRCUITS.get(provider_name)
    if not c:
        return {"provider": provider_name, "state": "closed", "failures": 0, "opened_at": None}
    state = "closed"
    if c["state"] == "open":
        reset_after = c.get("opened_at") or _now()
        if (_now() - reset_after).total_seconds() >= settings.circuit_breaker_reset_seconds:
            state = "half_open"
        else:
            state = "open"
    return {
        "provider": provider_name,
        "state": state,
        "failures": c.get("failures", 0),
        "opened_at": c.get("opened_at"),
        "threshold": settings.circuit_breaker_threshold,
        "reset_seconds": settings.circuit_breaker_reset_seconds,
    }


def circuit_ok(provider_name: str) -> bool:
    return circuit_status(provider_name)["state"] != "open"


def circuit_success(provider_name: str) -> None:
    _CIRCUITS.pop(provider_name, None)


def circuit_failure(provider_name: str) -> None:
    c = _CIRCUITS.setdefault(provider_name, {"failures": 0, "state": "closed", "opened_at": None})
    c["failures"] = c.get("failures", 0) + 1
    if c["failures"] >= settings.circuit_breaker_threshold:
        c["state"] = "open"
        c["opened_at"] = _now()
        log.error("Circuit OPEN for provider '%s' after %d consecutive failures",
                  provider_name, c["failures"])


def reset_circuits() -> None:
    _CIRCUITS.clear()


def run_with_fallback(
    primary: Callable[[], T],
    fallbacks: tuple[Callable[[], T], ...] = (),
    *,
    provider_name: str = "provider",
    max_retries: int | None = None,
    backoff_base: float | None = None,
    backoff_max: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log_error: bool = True,
) -> T:
    """Run `primary` with retries + backoff; if exhausted, try `fallbacks` once each.

    On total failure marks the circuit and raises ProviderUnavailableError with
    the last underlying exception chained.
    """
    if not circuit_ok(provider_name):
        raise ProviderUnavailableError(f"Provider '{provider_name}' unavailable (circuit open)")

    retries = max_retries if max_retries is not None else settings.max_retries_default
    if retries < 1:
        retries = 1
    base = backoff_base if backoff_base is not None else settings.retry_backoff_base_seconds
    cap = backoff_max if backoff_max is not None else settings.retry_backoff_max_seconds

    attempts: list[Callable[[], T]] = list(fallbacks)
    last_error: BaseException | None = None

    # primary: retry with exponential backoff
    for attempt in range(1, retries + 1):
        try:
            result = primary()
            circuit_success(provider_name)
            return result
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — any provider failure triggers fallback
            last_error = exc
            log.warning("primary '%s' attempt %d/%d failed: %s",
                        provider_name, attempt, retries, exc)
            if attempt < retries:
                sleep(min(base * (2 ** (attempt - 1)), cap))

    # fallbacks: one attempt each
    for fb in attempts:
        try:
            result = fb()
            circuit_success(provider_name)
            log.info("fallback provider succeeded for '%s'", provider_name)
            return result
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log.error("fallback for '%s' failed: %s", provider_name, exc)

    circuit_failure(provider_name)
    raise ProviderUnavailableError(
        f"Provider '{provider_name}' unavailable after {retries} attempts: {last_error}"
    ) from last_error