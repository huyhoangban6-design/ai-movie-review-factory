import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

log = logging.getLogger("app.request")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Phase 8 hardening: request_id xuyên suốt + security headers + request log.

    request_id: dùng header `settings.request_id_header` nếu có (tracing), else uuid.
    Python logging đóng vai trò structured log cho request; SystemLog table dùng
    cho sự kiện quan trọng (cost alerts, provider failures) ghi ở service layer.
    """

    def __init__(self, app: FastAPI, header_name: str = "x-request-id") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        request_id = request.headers.get(self.header_name) or uuid.uuid4().hex[:24]
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.error(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id, request.method, request.url.path, "500", duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers.setdefault(self.header_name, request_id)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)

        if request.url.path not in ("/health",):
            log.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id, request.method, request.url.path, response.status_code, duration_ms,
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window limiter cho auth endpoints.

    Phase 8: Redis backend optional qua REDIS_URL khi production scale (docs/14).
    """

    def __init__(self, app: FastAPI, limit: int, window_seconds: int, paths: tuple[str, ...]) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.paths = paths
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        if request.url.path in self.paths:
            client = request.client.host if request.client else "unknown"
            key = f"{client}:{request.url.path}"
            now = time.time()
            window = self._hits[key]
            while window and now - window[0] >= self.window_seconds:
                window.popleft()
            if len(window) >= self.limit:
                log.warning("rate_limited client=%s path=%s", client, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again shortly."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
            window.append(now)
        return await call_next(request)