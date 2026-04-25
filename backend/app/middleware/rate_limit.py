"""In-memory sliding-window rate limiter.

Process-local — fine for a single-instance demo / academic project. For a real production
deploy, swap the backing store for Redis. Keys are bucketed by:
  - the authenticated user id, when present, else
  - the client IP from X-Forwarded-For / request.client.

The limiter exposes two thresholds:
  - global, applied to every request
  - chat, applied additionally to /api/chat (which is by far the most expensive endpoint)
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


WINDOW_SECONDS = 60.0


class _SlidingWindow:
    def __init__(self) -> None:
        self._buckets: dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> tuple[bool, int, float]:
        """Returns (allowed, remaining, retry_after_seconds)."""
        if limit <= 0:
            return True, 0, 0.0
        now = time.monotonic()
        with self._lock:
            q = self._buckets.setdefault(key, deque())
            cutoff = now - WINDOW_SECONDS
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                retry_after = WINDOW_SECONDS - (now - q[0])
                return False, 0, max(retry_after, 0.1)
            q.append(now)
            return True, max(limit - len(q), 0), 0.0


_window = _SlidingWindow()


def _client_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return f"ip:{fwd.split(',')[0].strip()}"
    if request.client:
        return f"ip:{request.client.host}"
    return "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies the global limit; the chat-specific limit lives in a route dependency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        # Skip health and docs to keep them always reachable.
        path = request.url.path
        if path in {"/api/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        key = f"global:{_client_key(request)}"
        allowed, remaining, retry_after = _window.hit(key, settings.rate_limit_per_minute)
        if not allowed:
            return Response(
                status_code=429,
                content=f'{{"detail":"Rate limit exceeded. Retry after {retry_after:.1f}s."}}',
                media_type="application/json",
                headers={"Retry-After": f"{retry_after:.1f}"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def chat_rate_limit_dependency(request: Request) -> None:
    """FastAPI dependency that throttles the chat endpoint specifically."""
    key = f"chat:{_client_key(request)}"
    allowed, _remaining, retry_after = _window.hit(key, settings.rate_limit_chat_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Chat rate limit exceeded. Retry after {retry_after:.1f}s.",
            headers={"Retry-After": f"{retry_after:.1f}"},
        )


def reset_rate_limit_for_tests() -> None:
    with _window._lock:
        _window._buckets.clear()
