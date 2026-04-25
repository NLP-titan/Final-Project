"""SQLAlchemy engine, session, and Base class.

The engine is created lazily so that imports don't trigger filesystem writes (important for
test fixtures that override DATABASE_URL).
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # Ensure the parent directory exists for SQLite file paths.
        if "///" in url:
            path = url.split("///", 1)[1]
            if path and not path.startswith(":memory:"):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(url, future=True, pool_pre_ping=True)


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _build_engine(settings.database_url)
        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_engine_for_tests() -> None:
    """Drop cached engine/session — used by test fixtures that override DATABASE_URL."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency for a request-scoped DB session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
