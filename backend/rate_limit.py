"""In-memory rate limiter for API endpoints.

Uses a sliding window per (route_pattern, client_ip).
No external dependencies required.

Limits:
  /wallet/*        -- 10 requests/min
  /search/live*    -- 5 requests/min
  /search/fast     -- 30 requests/min
  all others       -- 120 requests/min (generous catch-all)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# (route_key) -> limit per 60 seconds
_LIMITS: list[tuple[str, int]] = [
    ("/wallet/", 10),
    ("/search/live", 5),
    ("/search/fast", 30),
]
_DEFAULT_LIMIT = 120
_WINDOW_SEC = 60


# ip -> route_key -> deque of timestamps
_windows: dict[str, dict[str, Deque[float]]] = defaultdict(lambda: defaultdict(deque))


def _route_key(path: str) -> str:
    for prefix, _ in _LIMITS:
        if path.startswith(prefix):
            return prefix
    return "__default__"


def _limit_for_key(key: str) -> int:
    for prefix, limit in _LIMITS:
        if key == prefix:
            return limit
    return _DEFAULT_LIMIT


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request) -> None:
    """Raise 429 if client has exceeded limit. Call from endpoint or middleware."""
    ip = _client_ip(request)
    key = _route_key(request.url.path)
    limit = _limit_for_key(key)

    now = time.monotonic()
    window = _windows[ip][key]

    # Evict timestamps older than window
    cutoff = now - _WINDOW_SEC
    while window and window[0] < cutoff:
        window.popleft()

    if len(window) >= limit:
        retry_after = int(_WINDOW_SEC - (now - window[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to all non-health routes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        # Skip health check from rate limiting
        if path in ("/health", "/"):
            return await call_next(request)
        try:
            check_rate_limit(request)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=dict(exc.headers or {}),
            )
        return await call_next(request)
