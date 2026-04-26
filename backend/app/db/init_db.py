"""Initialise the database, ensure an admin user exists, and seed reference data.

Idempotent — safe to call on every startup. Prefers Betty's prepared knowledge base when
present (under `KNOWLEDGE_BASE_DIR`); falls back to the small in-repo seed CSVs otherwise.
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
    _seed_reference_data()


def _seed_reference_data() -> None:
    """Seed the medicines and facilities tables from the best source available.

    Order of preference:
      1. The full knowledge base under KNOWLEDGE_BASE_DIR (Betty's package).
      2. The repo-bundled seed CSVs (small, kept for tests / fallback).
    Either way, we only seed when the target table is empty so we don't clobber admin edits.
    """
    kb_root = Path(settings.knowledge_base_dir)
    kb_facilities = kb_root / "database" / "nhis_hospitals.csv"
    kb_medicines = kb_root / "database" / "nhis_medicines_formulary_2025.csv"

    with session_scope() as db:
        if not db.execute(select(Medicine.id).limit(1)).first():
            if kb_medicines.exists():
                _seed_medicines_from_formulary(db, kb_medicines)
            else:
                _seed_medicines_from_simple_csv(db, Path(settings.medicines_csv))

        if not db.execute(select(Facility.id).limit(1)).first():
            if kb_facilities.exists():
                _seed_facilities_from_kb(db, kb_facilities)
            else:
                _seed_facilities_from_simple_csv(db, Path(settings.facilities_csv))


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


def _seed_medicines_from_simple_csv(db: Session, csv_path: Path) -> None:
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


def _seed_facilities_from_simple_csv(db: Session, csv_path: Path) -> None:
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


# ---------------------------------------------------------------------------
# Knowledge-base shaped sources (Betty's package)
# ---------------------------------------------------------------------------
_FORMULARY_HEADER_FIRST_COL = "NHIA Code"
_LEVEL_LABELS = {
    "A": "CHPS;Health Centre;District Hospital;Regional Hospital;Teaching Hospital",
    "B": "Health Centre;District Hospital;Regional Hospital;Teaching Hospital",
    "C": "District Hospital;Regional Hospital;Teaching Hospital",
    "D": "Regional Hospital;Teaching Hospital",
    "E": "Teaching Hospital",
}


def _level_label(code: str) -> str | None:
    code = (code or "").strip()
    if not code:
        return None
    head = code.split()[0].upper()
    return _LEVEL_LABELS.get(head, code)


def _split_town(town_field: str) -> tuple[str, str]:
    if "," in town_field:
        head, tail = town_field.split(",", 1)
        return head.strip(), tail.strip()
    return town_field.strip(), ""


def _seed_facilities_from_kb(db: Session, csv_path: Path) -> None:
    rows = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("facility_name") or "").strip()
            if not name:
                continue
            town, region_from_town = _split_town(row.get("town") or "")
            region = (row.get("region") or region_from_town or "").strip()
            accredited = _yes(row.get("nhis_accredited"))
            db.add(
                Facility(
                    name=name,
                    type=(row.get("facility_type") or "").strip() or None,
                    region=region or None,
                    district=None,
                    town=town or None,
                    accredited=accredited,
                    accreditation_status="Active" if accredited else "Not Accredited",
                    services=(row.get("services_offered") or "").strip() or None,
                    phone=(row.get("contact") or "").strip() or None,
                )
            )
            rows += 1
    log.info("Seeded %d facilities from knowledge base %s", rows, csv_path.name)


def _seed_medicines_from_formulary(db: Session, csv_path: Path) -> None:
    """Read Betty's nhis_medicines_formulary_2025.csv.

    Layout: BOM + 2 preamble rows + 1 header row + interleaved category-section rows
    (starting with "▸") + medicine rows.
    """
    rows = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        # Advance until we find the header row.
        header: list[str] | None = None
        for row in reader:
            if row and row[0].strip() == _FORMULARY_HEADER_FIRST_COL:
                header = [c.strip() for c in row]
                break
        if header is None:
            log.warning("Formulary header not found in %s", csv_path)
            return
        dict_reader = csv.DictReader(f, fieldnames=header)
        for row in dict_reader:
            if not row:
                continue
            code = (row.get(_FORMULARY_HEADER_FIRST_COL) or "").strip()
            if not code or code.startswith("▸"):
                continue
            generic = (row.get("Generic Name (INN)") or "").strip()
            if not generic:
                continue
            form = (row.get("Dosage Form") or "").strip()
            strength = (row.get("Strength") or "").strip()
            level = (row.get("Prescribing Level") or "").strip()
            price = (row.get("Price (GH₵)") or "").strip()
            category = (row.get("Category") or "").strip()
            on_list = _yes(row.get("On NHIS List"))
            notes_parts = [f"NHIA Code: {code}"]
            if price:
                notes_parts.append(f"Reference price: GH₵ {price}")
            if level:
                notes_parts.append(f"Prescribing Level: {level}")
            db.add(
                Medicine(
                    name=f"{generic} {form}".strip() or generic,
                    generic_name=generic,
                    strength=strength or None,
                    form=form or None,
                    therapeutic_class=category or None,
                    covered=on_list,
                    level_of_care=_level_label(level),
                    notes="; ".join(notes_parts),
                )
            )
            rows += 1
    log.info("Seeded %d medicines from knowledge base %s", rows, csv_path.name)
