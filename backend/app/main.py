"""FastAPI application entry."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.auth_router import router as auth_router
from app.api.conversations_router import router as conversations_router
from app.api.facilities_router import router as facilities_router
from app.api.feedback_router import router as feedback_router
from app.api.medicines_router import router as medicines_router
from app.api.policies_router import router as policies_router
from app.api.routes import router as core_router
from app.api.users_router import router as users_router
from app.config import settings
from app.db.init_db import init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.utils.logging import configure_logging


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    log.info("Starting NHIS Assistant backend")
    try:
        init_db()
        log.info("Database initialised")
    except Exception:
        log.exception("Database initialisation failed; continuing — endpoints may 500")
    yield
    log.info("Shutting down NHIS Assistant backend")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NHIS Assistant Backend",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "X-RateLimit-Remaining"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLogMiddleware)

    app.include_router(core_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(medicines_router, prefix="/api")
    app.include_router(facilities_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")
    app.include_router(policies_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        log.info(
            "validation error on %s %s: %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(request: Request, exc: IntegrityError):
        log.warning("DB integrity error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Database constraint violation"},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        log.exception("Unhandled error on %s %s rid=%s", request.method, request.url.path, request_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=False)
