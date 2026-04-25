"""Request-logging middleware: emits one line per request with method, path, status, duration."""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


log = logging.getLogger("nhis.access")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "rid=%s %s %s -> 500 %.1fms (unhandled)",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        user_id = getattr(request.state, "user_id", "-")
        log.info(
            "rid=%s user=%s %s %s -> %d %.1fms",
            request_id,
            user_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["x-request-id"] = request_id
        return response
