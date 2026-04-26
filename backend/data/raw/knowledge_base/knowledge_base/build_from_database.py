"""
Regenerate NHIS JSONL chunks from everything under database/*.csv and database/*.docx.

Run from repo root: python knowledge_base/build_from_database.py

- Discovers new datasets automatically (any new .csv / .docx in database/).
- Writes one JSONL per source: knowledge_base/sources/<stem>.jsonl
- Writes agent_system_context.jsonl (static guidance + optional NHIS Agent.docx at repo root)
- Concatenates knowledge_base/all_chunks.jsonl for single-file ingest
"""
from __future__ import annotations

import csv
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database"
OUT = Path(__file__).resolve().parent
OUT_SOURCES = OUT / "sources"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# --- IDs & slugs ---


def slug_id(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", s.strip(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:120] or "x"


def norm_header(h: str | None) -> str:
    if h is None:
        return ""
    return h.strip().lstrip("\ufeff")


# --- Handlers: row text ---


def row_to_facility_text(r: dict) -> str:
    name = (r.get("facility_name") or "").strip()
    code = (r.get("hospital_code") or "").strip()
    ftype = (r.get("facility_type") or "").strip()
    town = (r.get("town") or "").strip()
    region = (r.get("region") or "").strip()
    services = (r.get("services_offered") or "").strip()
    contact = (r.get("contact") or "").strip()
    acc = (r.get("nhis_accredited") or "").strip()
    parts = [
        f"{name} (NHIS facility listing code {code}) is a {ftype} in {town}, {region} Region, Ghana.",
        f"NHIS accreditation status in this dataset: {acc}.",
    ]
    if services:
        parts.append(f"Services or scope noted: {services}.")
    if contact:
        parts.append(f"Contact phone (as listed): {contact}.")
    parts.append(
        "Users can verify current accreditation with NHIA or the facility; this record is for entitlement guidance only."
    )
    return " ".join(parts)


def row_to_service_text(r: dict) -> str:
    sname = (r.get("service_name") or "").strip()
    code = (r.get("service_code") or "").strip()
    cat = (r.get("category") or "").strip()
    desc = (r.get("description") or "").strip()
    req = (r.get("facility_requirement") or "").strip()
    notes = (r.get("notes") or "").strip()
    if desc and not desc.endswith((".", "!", "?")):
        desc = desc + "."
    parts = [
        f"Under Ghana NHIS benefit-style listings, {sname} (service code {code}) is categorized as {cat}.",
        f"Description: {desc}",
        f"Typical facility requirement in this dataset: {req}.",
    ]
    if notes:
        parts.append(f"Additional notes: {notes}.")
    parts.append(
        "Coverage can depend on active membership, referral rules, and official NHIS policy updates; confirm disputed cases with NHIA."
    )
    return " ".join(parts)


def row_to_medicine_legacy_text(r: dict) -> str:
    name = (r.get("medicine_name") or "").strip()
    strength = (r.get("strength_formulation") or "").strip()
    cat = (r.get("category") or "").strip()
    prescriber = (r.get("prescriber_level") or "").strip()
    notes = (r.get("notes") or "").strip()
    parts = [
        f"{name} ({strength}) appears on this NHIS-style medicines listing.",
        f"Therapeutic category: {cat}.",
        f"Prescriber level in this dataset: {prescriber}.",
    ]
    if notes:
        parts.append(f"Notes: {notes}.")
    parts.append(
        "Whether a patient pays at point of care can still depend on stock, exact formulation, and facility dispensing rules; escalate billing disputes per NHIA guidance."
    )
    return " ".join(parts)


def row_to_formulary_2025_text(r: dict, source_stem: str) -> str:
    code = (r.get("NHIA Code") or "").strip()
    generic = (r.get("Generic Name (INN)") or "").strip()
    form = (r.get("Dosage Form") or "").strip()
    strength = (r.get("Strength") or "").strip()
    unit = (r.get("Unit of Pricing") or "").strip()
    price = (r.get("Price (GH₵)") or r.get("Price (GHc)") or "").strip()
    level = (r.get("Prescribing Level") or "").strip()
    cat = (r.get("Category") or "").strip()
    on_list = (r.get("On NHIS List") or "").strip()
    parts = [
        f"{generic} ({form}, {strength}) is listed on the 2025 NHIS medicines formulary with NHIA code {code}.",
        f"Category: {cat}. Prescribing level: {level}.",
        f"Unit of pricing: {unit}. Reference price in this extract: GH₵ {price}.",
        f"On NHIS list (per this dataset): {on_list}.",
        "Verify dispensing and copayment rules with the facility and current NHIA circulars.",
    ]
    return " ".join(parts)


def row_to_summary_category_text(r: dict) -> str:
    cat = (r.get("Category") or "").strip()
    n = (r.get("No. of Medicines") or r.get("No. of Medicines ") or "").strip()
    mn = (r.get("Min Price (GH₵)") or "").strip()
    mx = (r.get("Max Price (GH₵)") or "").strip()
    return (
        f"NHIS formulary summary — therapeutic category '{cat}': about {n} medicine line(s) in this category, "
        f"with indicative price range roughly GH₵ {mn} to GH₵ {mx} in this extracted table."
    )


def row_to_generic_csv_text(r: dict) -> str:
    pairs = []
    for k, v in r.items():
        kn = norm_header(k)
        if not kn:
            continue
        vv = (v or "").strip()
        if vv:
            pairs.append(f"{kn}: {vv}")
    return "; ".join(pairs) if pairs else ""


# --- CSV intelligence ---


CODE_RE = re.compile(r"^[A-Z]\d{3}$")


def find_csv_header_line(lines: list[str], must_contain: str) -> int | None:
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        first = line.split(",")[0].strip().lstrip("\ufeff")
        if first == must_contain or first.startswith(must_contain):
            return i
    return None


def read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (fieldnames, rows as dicts) using utf-8-sig."""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines(keepends=True)
    return lines, []  # rows filled by callers


def dicts_from_lines(header_line_idx: int, lines: list[str]) -> tuple[list[str], list[dict]]:
    buf = StringIO("".join(lines[header_line_idx:]))
    reader = csv.DictReader(buf)
    fieldnames = [norm_header(h) for h in (reader.fieldnames or [])]
    rows = []
    for row in reader:
        rows.append({norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return fieldnames, rows


def process_hospitals_csv(path: Path, stem: str) -> list[dict]:
    lines, _ = read_csv_rows(path)
    fieldnames, rows = dicts_from_lines(0, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=2):
        if not (row.get("hospital_code") or "").strip():
            continue
        hid = row["hospital_code"].strip()
        out.append(
            {
                "id": f"{stem}:facility:{hid}",
                "text": row_to_facility_text(row),
                "metadata": {
                    "domain": "facilities",
                    "chunk_type": "facility_record",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                    "hospital_code": hid,
                    "facility_type": (row.get("facility_type") or "").strip(),
                    "facility_name": (row.get("facility_name") or "").strip(),
                    "region": (row.get("region") or "").strip(),
                },
            }
        )
    return out


def process_services_csv(path: Path, stem: str) -> list[dict]:
    lines, _ = read_csv_rows(path)
    fieldnames, rows = dicts_from_lines(0, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=2):
        if not (row.get("service_code") or "").strip():
            continue
        sid = row["service_code"].strip()
        out.append(
            {
                "id": f"{stem}:service:{sid}",
                "text": row_to_service_text(row),
                "metadata": {
                    "domain": "coverage",
                    "chunk_type": "service_benefit",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                    "service_code": sid,
                    "category": (row.get("category") or "").strip(),
                    "service_name": (row.get("service_name") or "").strip(),
                },
            }
        )
    return out


def process_medicines_legacy_csv(path: Path, stem: str) -> list[dict]:
    lines, _ = read_csv_rows(path)
    fieldnames, rows = dicts_from_lines(0, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=2):
        name = (row.get("medicine_name") or "").strip()
        strength = (row.get("strength_formulation") or "").strip()
        if not name:
            continue
        mid = slug_id(f"{name}_{strength}")
        out.append(
            {
                "id": f"{stem}:medicine:{mid}",
                "text": row_to_medicine_legacy_text(row),
                "metadata": {
                    "domain": "medicines",
                    "chunk_type": "formulary_item",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                    "medicine_name": name,
                    "strength_formulation": strength,
                    "category": (row.get("category") or "").strip(),
                },
            }
        )
    return out


def process_formulary_2025_csv(path: Path, stem: str) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines(keepends=True)
    idx = find_csv_header_line(lines, "NHIA Code")
    if idx is None:
        idx = 0
    fieldnames, rows = dicts_from_lines(idx, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=idx + 2):
        code = (row.get("NHIA Code") or "").strip()
        generic = (row.get("Generic Name (INN)") or "").strip()
        if not code or not CODE_RE.match(code) or not generic:
            continue
        out.append(
            {
                "id": f"{stem}:nhia:{code}",
                "text": row_to_formulary_2025_text(row, stem),
                "metadata": {
                    "domain": "medicines",
                    "chunk_type": "formulary_2025_item",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                    "nhia_code": code,
                    "generic_name": generic,
                    "category": (row.get("Category") or "").strip(),
                },
            }
        )
    return out


def process_summary_by_category_csv(path: Path, stem: str) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines(keepends=True)
    # Row 0 is often a title; header is first line containing "Category"
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Category,"):
            header_idx = i
            break
        try:
            parts = next(csv.reader(StringIO(line.strip())))
        except StopIteration:
            continue
        if parts and norm_header(parts[0]) == "Category":
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0
    fieldnames, rows = dicts_from_lines(header_idx, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=header_idx + 2):
        cat = (row.get("Category") or "").strip()
        if not cat or cat.lower() == "category":
            continue
        out.append(
            {
                "id": f"{stem}:category:{slug_id(cat)}",
                "text": row_to_summary_category_text(row),
                "metadata": {
                    "domain": "medicines",
                    "chunk_type": "formulary_category_summary",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                    "therapeutic_category": cat,
                },
            }
        )
    return out


def process_lookup_guide_csv(path: Path, stem: str) -> list[dict]:
    """Two-column key / value guide without a standard header."""
    out: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, start=1):
            if not row:
                continue
            k = (row[0] or "").strip()
            v = (row[1] or "").strip() if len(row) > 1 else ""
            if not k and not v:
                continue
            if not v:
                text = f"NHIS knowledge lookup guide — {k}"
            else:
                text = f"NHIS knowledge lookup guide — {k}: {v}"
            kid = slug_id(k)[:80] or f"row{i}"
            out.append(
                {
                    "id": f"{stem}:guide:{kid}",
                    "text": text,
                    "metadata": {
                        "domain": "medicines",
                        "chunk_type": "lookup_guide",
                        "source_file": f"database/{path.name}",
                        "source_row": i,
                        "guide_key": k,
                    },
                }
            )
    return out


def process_generic_csv(path: Path, stem: str) -> list[dict]:
    lines, _ = read_csv_rows(path)
    fieldnames, rows = dicts_from_lines(0, lines)
    _ = fieldnames
    out: list[dict] = []
    for i, row in enumerate(rows, start=2):
        text = row_to_generic_csv_text(row)
        if not text:
            continue
        out.append(
            {
                "id": f"{stem}:row:{i}",
                "text": f"Record from {path.name}: {text}",
                "metadata": {
                    "domain": "coverage",
                    "chunk_type": "generic_csv_row",
                    "source_file": f"database/{path.name}",
                    "source_row": i,
                },
            }
        )
    return out


def detect_and_process_csv(path: Path) -> tuple[list[dict], str]:
    """Return (records, handler_name)."""
    stem = path.stem
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines(keepends=True)
    if not lines:
        return [], "empty"

    # Peek header row (first non-empty line) for detection
    first_data_line = 0
    for i, line in enumerate(lines):
        if line.strip():
            first_data_line = i
            break
    buf = StringIO("".join(lines[first_data_line:]))
    reader = csv.DictReader(buf)
    headers = {norm_header(h) for h in (reader.fieldnames or []) if norm_header(h)}

    if path.name.lower() == "lookup_guide.csv" or (
        "Prescribing Level A" in raw[:400] and "Lookup Guide" in raw[:500]
    ):
        return process_lookup_guide_csv(path, stem), "lookup_guide"

    if path.name.lower() == "summary_by_category.csv":
        return process_summary_by_category_csv(path, stem), "summary_by_category"

    # Formulary export: preamble lines before the real header — detect by filename or body
    low = path.name.lower()
    if "formulary" in low and "2025" in low:
        return process_formulary_2025_csv(path, stem), "formulary_2025"
    if "nhia code" in raw.lower()[:8000] and "generic name (inn)" in raw.lower()[:8000]:
        return process_formulary_2025_csv(path, stem), "formulary_2025"

    if {"hospital_code", "facility_name"}.issubset(headers):
        return process_hospitals_csv(path, stem), "hospitals"
    if {"service_code", "service_name"}.issubset(headers):
        return process_services_csv(path, stem), "services"
    if {"medicine_name", "strength_formulation"}.issubset(headers):
        return process_medicines_legacy_csv(path, stem), "medicines_legacy"
    if {"NHIA Code", "Generic Name (INN)"}.issubset(headers):
        return process_formulary_2025_csv(path, stem), "formulary_2025"

    return process_generic_csv(path, stem), "generic_csv"


# --- DOCX ---


def extract_docx_paragraphs(path: Path) -> list[str]:
    paras: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    for p in root.iter(f"{{{W_NS}}}p"):
        texts = [t.text for t in p.iter(f"{{{W_NS}}}t") if t.text]
        if texts:
            paras.append("".join(texts).strip())
    return [p for p in paras if p]


def merge_paragraphs_for_chunks(paragraphs: list[str], max_chars: int = 1400) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for p in paragraphs:
        add = len(p) + (2 if buf else 0)
        if buf and size + add > max_chars:
            chunks.append("\n\n".join(buf))
            buf = [p]
            size = len(p)
        else:
            if buf:
                size += 2
            buf.append(p)
            size += len(p)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def domain_for_docx_stem(stem: str) -> str:
    s = stem.lower()
    if "membership" in s or "enroll" in s or "renew" in s:
        return "enrollment"
    if "policy" in s or "benefit" in s or "rights" in s:
        return "coverage"
    if "dispute" in s or "complaint" in s:
        return "disputes"
    if "medicine" in s or "formulary" in s:
        return "medicines"
    if "hospital" in s or "facilit" in s:
        return "facilities"
    return "coverage"


def process_docx(path: Path) -> list[dict]:
    stem = slug_id(path.stem)
    paras = extract_docx_paragraphs(path)
    merged = merge_paragraphs_for_chunks(paras)
    dom = domain_for_docx_stem(path.stem)
    out: list[dict] = []
    for i, text in enumerate(merged):
        out.append(
            {
                "id": f"{stem}:docx:{i:04d}",
                "text": text,
                "metadata": {
                    "domain": dom,
                    "chunk_type": "document_paragraphs",
                    "source_file": f"database/{path.name}",
                    "chunk_index": i,
                },
            }
        )
    return out


# --- System chunks + optional root Agent docx ---


def load_system_chunks() -> list[dict]:
    return [
        {
            "id": "system:pipeline_overview",
            "text": (
                "The NHIS Patient Rights agent combines semantic retrieval over policy-style text "
                "with structured checks for medicines and facilities. Narrative policy documents "
                "are chunked by section for embedding; accredited facilities and the medicines "
                "formulary are treated as structured lists for exact or fuzzy lookup. The agent "
                "decides which path fits the user question."
            ),
            "metadata": {
                "domain": "system",
                "chunk_type": "architecture",
                "source": "NHIS Agent.docx",
            },
        },
        {
            "id": "system:kb_categories",
            "text": (
                "Knowledge for Ghana NHIS entitlement guidance is organized by category: coverage "
                "(what services and benefits apply), medicines (official formulary entries and "
                "prescriber levels), facilities (accreditation and facility type by region), "
                "enrollment (membership, registration, renewal), and disputes (denials, incorrect "
                "charges, and escalation). Each retrieved chunk should be tagged with one of "
                "these domains for filtering when needed."
            ),
            "metadata": {
                "domain": "system",
                "chunk_type": "taxonomy",
                "source": "NHIS Agent.docx",
            },
        },
        {
            "id": "system:rag_policy_vs_structured",
            "text": (
                "For RAG ingestion: narrative policy text (benefit package, membership guidelines, "
                "dispute procedures) belongs in a vector store with section-aware chunking, not "
                "arbitrary character splits. Structured lists such as accredited facilities and the "
                "medicines formulary are best stored as CSV or SQL for precise lookup; they can "
                "still be converted to natural-language records for hybrid search. Always cite "
                "source files and rows when answering."
            ),
            "metadata": {
                "domain": "system",
                "chunk_type": "rag_guidance",
                "source": "NHIS Agent.docx",
            },
        },
        {
            "id": "system:evaluation_scenarios",
            "text": (
                "Evaluation scenarios for the agent include: coverage queries (e.g. whether dialysis "
                "or surgery types are covered), drug entitlement (whether a medication should be "
                "charged), facility accreditation (whether a hospital is NHIS-accredited), "
                "membership and renewal (expired card, re-registration), and rights disputes "
                "(being turned away or charged for covered care). Aim for diverse test cases across "
                "these intents."
            ),
            "metadata": {
                "domain": "system",
                "chunk_type": "evaluation",
                "source": "NHIS Agent.docx",
            },
        },
        {
            "id": "system:disclaimer_escalation",
            "text": (
                "When policy text is silent, sources conflict, or the situation is urgent or "
                "high-stakes, the agent should escalate: suggest contacting NHIA or the relevant "
                "regional office, collecting receipts and NHIS ID, and using official channels. "
                "Do not present model guesses as legal determinations of entitlement."
            ),
            "metadata": {
                "domain": "disputes",
                "chunk_type": "escalation",
                "source": "NHIS Agent.docx",
            },
        },
        {
            "id": "system:sources_to_collect",
            "text": (
                "Authoritative sources to grow the knowledge base include: the NHIS benefit package "
                "document, the official NHIS medicines list, accredited facilities by region, "
                "membership registration and renewal guidelines, and common denial or dispute "
                "resolution procedures. New material should be tagged by category and effective "
                "date when known. Place new datasets in the database/ folder and run build_from_database.py."
            ),
            "metadata": {
                "domain": "enrollment",
                "chunk_type": "source_inventory",
                "source": "NHIS Agent.docx",
            },
        },
    ]


def optional_root_agent_docx_chunks() -> list[dict]:
    path = ROOT / "NHIS Agent.docx"
    if not path.is_file():
        return []
    records = process_docx(path)
    for r in records:
        idx = r["metadata"].get("chunk_index", 0)
        r["id"] = f"root_agent_docx:{idx:04d}"
        r["metadata"]["source_file"] = path.name
        r["metadata"]["chunk_type"] = "agent_spec_document"
        r["metadata"]["domain"] = "system"
    return records


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    OUT_SOURCES.mkdir(parents=True, exist_ok=True)
    # Remove stale generated shards so deleted database files do not leave ghost JSONL
    for p in OUT_SOURCES.glob("*.jsonl"):
        p.unlink()

    manifest: dict = {
        "kb_name": "ghana_nhis_entitlement_kb",
        "version": "2.0.0",
        "embedding_field": "text",
        "id_field": "id",
        "database_dir": "database",
        "sources_dir": "knowledge_base/sources",
        "metadata_fields": ["domain", "chunk_type", "source_file", "source_row"],
        "collections": [],
    }

    all_counts: dict[str, int] = {}
    part_paths: list[Path] = []

    csv_files = sorted(DB.glob("*.csv"), key=lambda p: p.name.lower())
    docx_files = sorted(DB.glob("*.docx"), key=lambda p: p.name.lower())

    for path in csv_files:
        rel = f"database/{path.name}"
        try:
            records, handler = detect_and_process_csv(path)
        except Exception as e:
            manifest["collections"].append(
                {
                    "source": rel,
                    "output": f"sources/{path.stem}.jsonl",
                    "chunk_count": 0,
                    "handler": "error",
                    "error": str(e),
                }
            )
            continue
        out_path = OUT_SOURCES / f"{path.stem}.jsonl"
        write_jsonl(out_path, records)
        all_counts[out_path.name] = len(records)
        part_paths.append(out_path)
        manifest["collections"].append(
            {
                "source": rel,
                "output": f"sources/{path.stem}.jsonl",
                "chunk_count": len(records),
                "handler": handler,
            }
        )

    for path in docx_files:
        rel = f"database/{path.name}"
        try:
            records = process_docx(path)
        except Exception as e:
            manifest["collections"].append(
                {
                    "source": rel,
                    "output": f"sources/{path.stem}.jsonl",
                    "chunk_count": 0,
                    "handler": "docx",
                    "error": str(e),
                }
            )
            continue
        out_path = OUT_SOURCES / f"{path.stem}.jsonl"
        write_jsonl(out_path, records)
        all_counts[out_path.name] = len(records)
        part_paths.append(out_path)
        manifest["collections"].append(
            {
                "source": rel,
                "output": f"sources/{path.stem}.jsonl",
                "chunk_count": len(records),
                "handler": "docx",
            }
        )

    sys_chunks = load_system_chunks() + optional_root_agent_docx_chunks()
    out_sys = OUT / "agent_system_context.jsonl"
    write_jsonl(out_sys, sys_chunks)
    all_counts["agent_system_context.jsonl"] = len(sys_chunks)

    manifest["collections"].append(
        {
            "source": "knowledge_base/build_from_database.py (static + optional root NHIS Agent.docx)",
            "output": "agent_system_context.jsonl",
            "chunk_count": len(sys_chunks),
            "handler": "system",
        }
    )

    manifest["total_chunks"] = sum(all_counts.values())
    manifest["files"] = all_counts

    combined_path = OUT / "all_chunks.jsonl"
    order = [out_sys] + sorted(part_paths, key=lambda p: p.name.lower())
    with combined_path.open("w", encoding="utf-8") as out:
        for part in order:
            with part.open(encoding="utf-8") as inf:
                out.write(inf.read())
    manifest["combined_file"] = "all_chunks.jsonl"
    manifest["combined_chunk_count"] = manifest["total_chunks"]

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Legacy top-level duplicates removed — consumers should use sources/ + manifest
    for legacy in ("nhis_facilities.jsonl", "nhis_services.jsonl", "nhis_medicines.jsonl"):
        lp = OUT / legacy
        if lp.is_file():
            lp.unlink()

    print("Wrote:", manifest_path)
    print("Wrote:", combined_path)
    print("Per-source outputs in:", OUT_SOURCES)
    for item in manifest["collections"]:
        if item.get("error"):
            print(f"  ERROR {item['source']}: {item['error']}")
        else:
            print(f"  {item.get('output', item)}: {item.get('chunk_count', '')} ({item.get('handler', '')})")


if __name__ == "__main__":
    main()
