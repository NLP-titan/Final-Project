"""Initialise the database, ensure an admin user exists, and seed reference data from CSV.

Idempotent — safe to call on every startup.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.db.base import Base, get_engine, session_scope
from app.db.models import Facility, Medicine, User


log = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
    with session_scope() as db:
        _ensure_admin(db)
        _seed_medicines(db)
        _seed_facilities(db)


def _ensure_admin(db: Session) -> None:
    has_admin = db.execute(select(User).where(User.role == "admin")).scalar_one_or_none()
    if has_admin:
        return
    email = settings.initial_admin_email
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        existing.role = "admin"
        log.info("Promoted existing user %s to admin", email)
        return
    admin = User(
        email=email,
        full_name="System Admin",
        hashed_password=hash_password(settings.initial_admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    log.info("Created initial admin user %s", email)


def _yes(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"yes", "true", "1", "y"}


def _seed_medicines(db: Session) -> None:
    if db.execute(select(Medicine.id).limit(1)).first():
        return
    csv_path = Path(settings.medicines_csv)
    if not csv_path.exists():
        log.warning("Medicines CSV not found at %s — skipping seed", csv_path)
        return
    rows = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add(
                Medicine(
                    name=row.get("name", "").strip(),
                    generic_name=row.get("generic_name", "").strip(),
                    strength=row.get("strength") or None,
                    form=row.get("form") or None,
                    therapeutic_class=row.get("therapeutic_class") or None,
                    covered=_yes(row.get("covered", "yes")),
                    level_of_care=row.get("level_of_care") or None,
                    notes=row.get("notes") or None,
                )
            )
            rows += 1
    log.info("Seeded %d medicines from %s", rows, csv_path)


def _seed_facilities(db: Session) -> None:
    if db.execute(select(Facility.id).limit(1)).first():
        return
    csv_path = Path(settings.facilities_csv)
    if not csv_path.exists():
        log.warning("Facilities CSV not found at %s — skipping seed", csv_path)
        return
    rows = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add(
                Facility(
                    name=row.get("name", "").strip(),
                    type=row.get("type") or None,
                    region=row.get("region") or None,
                    district=row.get("district") or None,
                    town=row.get("town") or None,
                    accredited=_yes(row.get("accredited", "yes")),
                    accreditation_status=row.get("accreditation_status") or None,
                    services=row.get("services") or None,
                    phone=row.get("phone") or None,
                )
            )
            rows += 1
    log.info("Seeded %d facilities from %s", rows, csv_path)
