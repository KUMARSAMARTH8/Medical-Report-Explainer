"""
utils/rate_limit.py

A minimal in-memory rate limiter, keyed by client IP, using a sliding
one-minute window. Good enough to stop accidental hammering of the API in
a demo/portfolio deployment without adding Redis or another dependency.

For real production traffic, swap this for `slowapi` + Redis — this is
intentionally simple so the project has zero extra infra to run.
"""

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Rate-limit API traffic only; static CSS/JS/assets should never consume the API quota.
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        limit = settings.rate_limit_per_minute
        if limit <= 0:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        hits = self._hits[client_ip]

        # Drop timestamps outside the sliding window
        while hits and now - hits[0] > _WINDOW_SECONDS:
            hits.popleft()

        if len(hits) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again shortly."},
            )

        hits.append(now)
        return await call_next(request)
