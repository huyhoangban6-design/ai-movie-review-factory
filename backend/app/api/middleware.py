import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window limiter cho auth endpoints.

    Phase 8 sẽ thay bằng Redis (dùng backend chung qua REDIS_URL).
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
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again shortly."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
            window.append(now)
        return await call_next(request)