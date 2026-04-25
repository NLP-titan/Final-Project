"""Pytest fixtures.

Each test gets a fresh in-memory SQLite database with seeded medicines, facilities, and an
admin user. The vector store / sentence-transformer model is *not* loaded — RAG-dependent
tests are kept in their own modules and skipped when chromadb isn't installed.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use a clean tmp DB per test module before any app modules are imported.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="nhis-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DIR / 'test.db'}")
os.environ.setdefault("JWT_SECRET", "test-secret-please-make-this-at-least-32-bytes-long")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_CHAT_PER_MINUTE", "200")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path) -> Iterator[None]:
    """Point each test at its own SQLite file so state doesn't leak between tests."""
    from app.config import settings as app_settings
    from app.db import base as db_base

    db_file = tmp_path / "test.db"
    monkeypatch.setattr(app_settings, "database_url", f"sqlite:///{db_file}")

    db_base.reset_engine_for_tests()
    from app.db.init_db import init_db

    init_db()
    yield
    db_base.reset_engine_for_tests()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.middleware.rate_limit import reset_rate_limit_for_tests

    reset_rate_limit_for_tests()
    return TestClient(create_app())


@pytest.fixture
def admin_token(client) -> str:
    from app.config import settings as app_settings

    resp = client.post(
        "/api/auth/login",
        json={
            "email": app_settings.initial_admin_email,
            "password": app_settings.initial_admin_password,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_token(client) -> str:
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "supersecret123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def user_headers(user_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}
