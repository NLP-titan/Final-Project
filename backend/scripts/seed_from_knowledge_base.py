"""Ingest Betty's `knowledge_base/` package.

What it does:
  1. Reads `<KB>/knowledge_base/all_chunks.jsonl` and embeds every chunk into ChromaDB. Each
     chunk's metadata is preserved verbatim (id, domain, chunk_type, source_file, source_row,
     plus any extra fields). Existing chunks with the same id are upserted.
  2. Reads `<KB>/database/nhis_hospitals.csv` and upserts rows into the `facilities` table.
  3. Reads `<KB>/database/nhis_medicines_formulary_2025.csv` and upserts rows into the
     `medicines` table. The formulary CSV has a BOM, two preamble rows, then a header, then
     category-section markers (rows starting with "▸") interleaved with medicine rows — those
     section markers are skipped.

Idempotent: re-running picks up Betty's regenerated outputs without duplicates.

Usage from the backend directory:
    python -m scripts.seed_from_knowledge_base                     # incremental upsert
    python -m scripts.seed_from_knowledge_base --reset-vector-store
    python -m scripts.seed_from_knowledge_base --kb /path/to/kb
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

# Allow running as `python scripts/seed_from_knowledge_base.py` from the backend root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.base import session_scope  # noqa: E402
from app.db.models import Facility, Medicine  # noqa: E402
from app.rag.chunker import Chunk  # noqa: E402
from app.rag.vector_store import PolicyVectorStore  # noqa: E402


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _yes(v: object) -> bool:
    if isinstance(v, bool):
        return v
    return str(v or "").strip().lower() in {"yes", "true", "1", "y"}


def _kb_root() -> Path:
    return Path(settings.knowledge_base_dir)


def _level_label(code: str) -> str:
    code = (code or "").strip()
    head = code.split()[0].upper() if code else ""
    mapping = {
        "A": "CHPS;Health Centre;District Hospital;Regional Hospital;Teaching Hospital",
        "B": "Health Centre;District Hospital;Regional Hospital;Teaching Hospital",
        "C": "District Hospital;Regional Hospital;Teaching Hospital",
        "D": "Regional Hospital;Teaching Hospital",
        "E": "Teaching Hospital",
    }
    return mapping.get(head, code)


def _split_town(town_field: str) -> tuple[str, str]:
    """Betty's `town` column is sometimes 'City, Region' — split when it is."""
    if "," in town_field:
        head, tail = town_field.split(",", 1)
        return head.strip(), tail.strip()
    return town_field.strip(), ""


# ---------------------------------------------------------------------------
# Vector store ingest
# ---------------------------------------------------------------------------
def ingest_chunks_jsonl(path: Path, reset: bool = False) -> int:
    if not path.exists():
        log.warning("all_chunks.jsonl not found at %s — skipping vector ingest", path)
        return 0

    store = PolicyVectorStore()
    if reset:
        store.reset()

    chunks: list[Chunk] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                log.warning("skipping invalid JSON on line %d: %s", line_no, exc)
                continue
            text = (record.get("text") or "").strip()
            if not text:
                continue
            meta = dict(record.get("metadata") or {})
            meta.setdefault("source_file", meta.get("source_file") or path.name)
            # Map Betty's `domain` onto our `category` so the policy retriever's filter works.
            if "category" not in meta and meta.get("domain"):
                meta["category"] = _normalise_category(str(meta["domain"]))
            if record.get("id"):
                meta["external_id"] = record["id"]
            chunks.append(Chunk(text=text, metadata=meta))

    if not chunks:
        log.info("No chunks found in %s", path)
        return 0

    added = store.add(chunks)
    log.info("Embedded %d chunks from %s (collection now has %d)", added, path.name, store.count())
    return added


CATEGORY_ALIASES = {
    "facility": "facilities",
    "facilities": "facilities",
    "medicine": "medicines",
    "medicines": "medicines",
    "drug": "medicines",
    "drugs": "medicines",
    "formulary": "medicines",
    "service": "services",
    "services": "services",
    "coverage": "coverage",
    "benefits": "coverage",
    "exclusions": "coverage",
    "membership": "enrollment",
    "enrolment": "enrollment",
    "enrollment": "enrollment",
    "renewal": "enrollment",
    "policy": "policy",
    "legal": "policy",
    "complaints": "disputes",
    "disputes": "disputes",
    "rights": "disputes",
    "system": "system",
    "general": "general",
}


def _normalise_category(raw: str) -> str:
    return CATEGORY_ALIASES.get(raw.strip().lower(), raw.strip().lower())


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------
def ingest_facilities(path: Path) -> int:
    if not path.exists():
        log.warning("nhis_hospitals.csv not found at %s — skipping facilities", path)
        return 0
    rows_seen = 0
    with session_scope() as db, path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("facility_name") or "").strip()
            if not name:
                continue
            town, region_from_town = _split_town(row.get("town") or "")
            region = (row.get("region") or region_from_town or "").strip()
            existing = db.execute(
                select(Facility).where(Facility.name == name)
            ).scalar_one_or_none()
            payload = {
                "name": name,
                "type": (row.get("facility_type") or "").strip() or None,
                "region": region or None,
                "district": None,
                "town": town or None,
                "accredited": _yes(row.get("nhis_accredited")),
                "accreditation_status": "Active" if _yes(row.get("nhis_accredited")) else "Not Accredited",
                "services": (row.get("services_offered") or "").strip() or None,
                "phone": (row.get("contact") or "").strip() or None,
            }
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
                db.add(existing)
            else:
                db.add(Facility(**payload))
            rows_seen += 1
    log.info("Upserted %d facilities from %s", rows_seen, path.name)
    return rows_seen


# ---------------------------------------------------------------------------
# Medicines
# ---------------------------------------------------------------------------
FORMULARY_HEADER = (
    "NHIA Code",
    "Generic Name (INN)",
    "Dosage Form",
    "Strength",
    "Unit of Pricing",
    "Price (GH₵)",
    "Prescribing Level",
    "Category",
    "On NHIS List",
)


def ingest_medicines(path: Path) -> int:
    if not path.exists():
        log.warning("nhis_medicines_formulary_2025.csv not found at %s — skipping medicines", path)
        return 0
    rows_seen = 0
    f = path.open("r", encoding="utf-8-sig", newline="")
    try:
        reader = csv.reader(f)
        # Advance to the header row.
        for row in reader:
            if row and row[0].strip() == FORMULARY_HEADER[0]:
                header = [c.strip() for c in row]
                break
        else:
            raise ValueError(f"Header row not found in {path}")
        dict_reader = csv.DictReader(f, fieldnames=header)

        with session_scope() as db:
            for row in dict_reader:
                if not row:
                    continue
                code = (row.get("NHIA Code") or "").strip()
                if not code or code.startswith("▸"):
                    continue
                generic = (row.get("Generic Name (INN)") or "").strip()
                form = (row.get("Dosage Form") or "").strip()
                strength = (row.get("Strength") or "").strip()
                if not generic:
                    continue
                # Compose a display name from generic + form so duplicates collide nicely.
                name = f"{generic} {form}".strip()
                level = (row.get("Prescribing Level") or "").strip()
                price = (row.get("Price (GH₵)") or "").strip()
                category = (row.get("Category") or "").strip()
                on_list = _yes(row.get("On NHIS List"))
                notes_parts = []
                if code:
                    notes_parts.append(f"NHIA Code: {code}")
                if price:
                    notes_parts.append(f"Reference price: GH₵ {price}")
                if level:
                    notes_parts.append(f"Prescribing Level: {level}")
                notes = "; ".join(notes_parts) or None

                existing = db.execute(
                    select(Medicine).where(
                        Medicine.generic_name == generic,
                        Medicine.form == form,
                        Medicine.strength == strength,
                    )
                ).scalar_one_or_none()
                payload = {
                    "name": name or generic,
                    "generic_name": generic,
                    "strength": strength or None,
                    "form": form or None,
                    "therapeutic_class": category or None,
                    "covered": on_list,
                    "level_of_care": _level_label(level),
                    "notes": notes,
                }
                if existing:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                    db.add(existing)
                else:
                    db.add(Medicine(**payload))
                rows_seen += 1
    finally:
        f.close()
    log.info("Upserted %d medicines from %s", rows_seen, path.name)
    return rows_seen


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DB + vector store from knowledge_base/")
    parser.add_argument(
        "--kb",
        default=None,
        help=f"Knowledge base root (default: {settings.knowledge_base_dir}).",
    )
    parser.add_argument(
        "--reset-vector-store",
        action="store_true",
        help="Drop and rebuild the ChromaDB collection before ingest.",
    )
    parser.add_argument(
        "--skip-vector",
        action="store_true",
        help="Skip the all_chunks.jsonl ingest (just refresh structured tables).",
    )
    parser.add_argument(
        "--skip-structured",
        action="store_true",
        help="Skip the medicines/facilities CSV ingest (just refresh the vector store).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    kb_root = Path(args.kb) if args.kb else _kb_root()
    if not kb_root.exists():
        log.error("Knowledge base directory not found: %s", kb_root)
        return 1
    log.info("Using knowledge base at %s", kb_root)

    chunks_path = kb_root / "knowledge_base" / "all_chunks.jsonl"
    facilities_path = kb_root / "database" / "nhis_hospitals.csv"
    medicines_path = kb_root / "database" / "nhis_medicines_formulary_2025.csv"

    if not args.skip_vector:
        ingest_chunks_jsonl(chunks_path, reset=args.reset_vector_store)
    if not args.skip_structured:
        ingest_facilities(facilities_path)
        ingest_medicines(medicines_path)

    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
