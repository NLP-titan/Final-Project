"""Initialise the database, ensure an admin user exists, and seed reference data.

Idempotent — safe to call on every startup. Prefers Betty's prepared knowledge base when
present (under `KNOWLEDGE_BASE_DIR`); falls back to the small in-repo seed CSVs otherwise.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.db.base import Base, get_engine, session_scope
from app.db.models import Facility, HealthUpdate, Medicine, Resource, User


log = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
    _apply_lightweight_migrations()
    with session_scope() as db:
        _ensure_admin(db)
    _seed_reference_data()
    _seed_content_data()
    _geocode_facilities_offline()


# Map of table -> list of (column_name, column_ddl) we want to ensure exists.
# SQLite's `ALTER TABLE ... ADD COLUMN` is the simplest forward migration we can do
# without pulling in Alembic. Keep entries idempotent.
_REQUIRED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "facilities": [
        ("lat", "FLOAT"),
        ("lng", "FLOAT"),
    ],
    "health_updates": [
        ("source_url", "VARCHAR(1024)"),
    ],
    "users": [
        ("language_preference", "VARCHAR(8) NOT NULL DEFAULT 'en'"),
    ],
}


def _apply_lightweight_migrations() -> None:
    engine = get_engine()
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _REQUIRED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns:
                if name in existing:
                    continue
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    log.info("Added column %s.%s", table, name)
                except Exception as exc:
                    log.warning("Could not add column %s.%s: %s", table, name, exc)


def _geocode_facilities_offline() -> None:
    """Apply the offline town-centroid lookup to any facility missing coords.
    Network-based geocoding is left to `scripts.geocode_facilities`."""
    try:
        from scripts.geocode_facilities import _lookup_offline  # type: ignore
    except Exception:
        return
    with session_scope() as db:
        rows = db.execute(
            select(Facility).where((Facility.lat.is_(None)) | (Facility.lng.is_(None)))
        ).scalars().all()
        hits = 0
        for row in rows:
            coords = _lookup_offline(row.town)
            if coords:
                row.lat, row.lng = coords
                hits += 1
        if hits:
            log.info("Backfilled lat/lng for %d facilities (offline lookup)", hits)


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


def _seed_content_data() -> None:
    with session_scope() as db:
        if not db.execute(select(HealthUpdate.id).limit(1)).first():
            _seed_health_updates(db)
        if not db.execute(select(Resource.id).limit(1)).first():
            _seed_resources(db)


def _seed_health_updates(db: Session) -> None:
    updates = [
        HealthUpdate(title="New Antimalarial Drugs Added to NHIS Formulary", source="NHIS Official", category="Drug Formulary", summary="New artemisinin-based combination therapies have been approved and added to the NHIS Essential Medicines List, improving access for malaria patients at accredited facilities.", published_date="24 May, 2025"),
        HealthUpdate(title="Nationwide Polio Vaccination Campaign", source="Ghana Health Service", category="Disease Alerts", summary="Ghana Health Service is conducting a nationwide polio vaccination campaign targeting children under five. Visit your nearest NHIS-accredited health facility to participate.", published_date="12 March, 2025"),
        HealthUpdate(title="Digital Renewal System Scheduled Maintenance", source="NHIS IT Dept", category="Policy Updates", summary="The *929# USSD renewal system will be offline for scheduled maintenance. Members are advised to visit district offices or use the NHIA mobile app during this period.", published_date="05 March, 2025"),
        HealthUpdate(title="Maternal Care Package Expanded", source="NHIS Official", category="Policy Updates", summary="NHIS has expanded its maternal care package to include additional antenatal visits and postnatal counselling sessions at no cost to registered members.", published_date="18 Feb, 2025"),
        HealthUpdate(title="Cholera Outbreak Precautionary Measures", source="Ghana Health Service", category="Disease Alerts", summary="Following reports of cholera cases in parts of Greater Accra, the Ghana Health Service urges all residents to maintain proper hygiene. NHIS covers cholera treatment at accredited facilities.", published_date="10 Feb, 2025"),
        HealthUpdate(title="NHIS Card Replacement Process Simplified", source="NHIS Official", category="Policy Updates", summary="Lost or damaged NHIS cards can now be replaced at any district office with a valid Ghana Card. The fee has been waived for indigent members.", published_date="02 Jan, 2025"),
    ]
    for u in updates:
        db.add(u)
    log.info("Seeded %d health updates", len(updates))


def _seed_resources(db: Session) -> None:
    resources = [
        Resource(title="Understanding Your NHIS Card", category="Membership", read_time="3 min", content="Your NHIS card is your gateway to free or subsidised healthcare at over 4,000 accredited facilities across Ghana. It contains your NHIS number, membership type, and expiry date. Always carry it when visiting a health facility. Your membership type determines your premium: SSNIT contributors pay through their monthly deductions, informal sector workers pay a flat annual premium, and indigents are enrolled for free."),
        Resource(title="What Services Are Excluded from NHIS?", category="Covered Services", read_time="5 min", content="While NHIS covers a broad range of services, some are explicitly excluded. These include: cosmetic surgery, private ward accommodation above the NHIS rate, assisted reproduction (IVF), most cancer treatments beyond surgery, dialysis for chronic kidney disease, and overseas treatment. Emergency stabilisation is always covered regardless of exclusion status. If you believe a covered service has been wrongly denied, you have the right to file a complaint."),
        Resource(title="How to Dispute an Unfair Charge", category="Your Rights", read_time="4 min", content="If an accredited facility charges you for a service or medicine that should be free under NHIS, you have the right to dispute it. Step 1: Ask for an itemised receipt. Step 2: Contact the NHIA district office in your area. Step 3: File a formal complaint using the NHIA complaint form (available at district offices or nhis.gov.gh). Step 4: The facility has 14 days to respond. The NHIA will investigate and can sanction facilities found to be in breach. Keep all receipts and documents."),
        Resource(title="Checking if Your Medication is Covered", category="Medicines Guide", read_time="2 min", content="NHIS covers a defined list of medicines called the Essential Medicines List. To check if a drug is covered: use the Medicines Checker tool in this app, ask the NHIS Agent, or consult the full list at nhis.gov.gh. Generics are always preferred. If your doctor prescribes a branded drug and the generic equivalent is on the list, the facility should dispense the generic at no cost. If a covered drug is out of stock, request documentation and the facility should arrange a substitute."),
        Resource(title="Enrollment and Renewal Steps", category="Enrollment", read_time="4 min", content="New enrollment: Visit any NHIS district office with your Ghana Card and one passport photo. Pay the applicable premium (informal sector). Your card is activated within 3 months. Renewal: Dial *929# on any network, use the NHIA mobile app, or visit your district office. Bring your expired card and Ghana Card. SSNIT members renew automatically through payroll. Pregnant women are enrolled free at any NHIS-accredited facility. Your coverage remains active for 12 months from the renewal date."),
        Resource(title="Frequently Asked Questions", category="FAQs", read_time="6 min", content="Q: Can I use NHIS at any hospital? Only NHIS-accredited facilities. Use the Facility Finder in this app to locate one near you. Q: What if I forget my card? Most facilities can verify your membership using your Ghana Card and NHIS number. Q: Does NHIS cover my children? Yes, dependants under 18 are covered under a family enrollment. Q: Can I use NHIS in another region? Yes, your card is valid at any accredited facility nationwide. Q: What happens if my card expires? You lose coverage until you renew. Emergency stabilisation may still be provided — ask the facility and contact NHIA if denied."),
    ]
    for r in resources:
        db.add(r)
    log.info("Seeded %d resources", len(resources))


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
                    lat=None,
                    lng=None,
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
