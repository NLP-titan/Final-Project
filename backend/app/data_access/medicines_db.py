"""Medicines lookup. DB-backed (with the CSV used as one-time seed during init_db)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import session_scope
from app.db.models import Medicine


@dataclass
class MedicineMatch:
    id: int
    name: str
    generic_name: str
    strength: str
    form: str
    therapeutic_class: str
    covered: bool
    level_of_care: list[str]
    notes: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def _split_levels(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


def _row_to_match(row: Medicine, score: float) -> MedicineMatch:
    return MedicineMatch(
        id=row.id,
        name=row.name or "",
        generic_name=row.generic_name or "",
        strength=row.strength or "",
        form=row.form or "",
        therapeutic_class=row.therapeutic_class or "",
        covered=bool(row.covered),
        level_of_care=_split_levels(row.level_of_care),
        notes=row.notes or "",
        score=score,
    )


def _search(db: Session, query: str, limit: int, min_score: float) -> list[MedicineMatch]:
    query = query.strip()
    if not query:
        return []
    rows = db.execute(select(Medicine)).scalars().all()
    candidates: list[tuple[Medicine, float]] = []
    for row in rows:
        haystacks = [row.name or "", row.generic_name or ""]
        best = max((fuzz.WRatio(query, h) for h in haystacks if h), default=0)
        if best >= min_score:
            candidates.append((row, float(best)))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [_row_to_match(row, score) for row, score in candidates[:limit]]


def search_medicine(query: str, limit: int = 5, min_score: float = 75.0) -> list[MedicineMatch]:
    with session_scope() as db:
        return _search(db, query, limit, min_score)


def search_medicine_with_session(
    db: Session, query: str, limit: int = 5, min_score: float = 75.0
) -> list[MedicineMatch]:
    return _search(db, query, limit, min_score)
