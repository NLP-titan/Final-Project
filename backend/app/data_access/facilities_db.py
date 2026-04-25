"""Facilities lookup. DB-backed (with the CSV used as one-time seed during init_db)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import session_scope
from app.db.models import Facility


@dataclass
class FacilityMatch:
    id: int
    name: str
    type: str
    region: str
    district: str
    town: str
    accredited: bool
    accreditation_status: str
    services: list[str]
    phone: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def _split_services(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


def _row_to_match(row: Facility, score: float) -> FacilityMatch:
    return FacilityMatch(
        id=row.id,
        name=row.name or "",
        type=row.type or "",
        region=row.region or "",
        district=row.district or "",
        town=row.town or "",
        accredited=bool(row.accredited),
        accreditation_status=row.accreditation_status or "",
        services=_split_services(row.services),
        phone=row.phone or "",
        score=score,
    )


def _search(
    db: Session,
    query: str,
    region: str | None,
    limit: int,
    min_score: float,
) -> list[FacilityMatch]:
    query = query.strip()
    if not query:
        return []
    stmt = select(Facility)
    if region:
        stmt = stmt.where(Facility.region.ilike(region.strip()))
    rows = db.execute(stmt).scalars().all()

    candidates: list[tuple[Facility, float]] = []
    for row in rows:
        haystacks = [row.name or "", row.town or "", row.district or ""]
        best = max((fuzz.WRatio(query, h) for h in haystacks if h), default=0)
        if best >= min_score:
            candidates.append((row, float(best)))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [_row_to_match(row, score) for row, score in candidates[:limit]]


def search_facility(
    query: str,
    region: str | None = None,
    limit: int = 5,
    min_score: float = 65.0,
) -> list[FacilityMatch]:
    with session_scope() as db:
        return _search(db, query, region, limit, min_score)


def search_facility_with_session(
    db: Session,
    query: str,
    region: str | None = None,
    limit: int = 5,
    min_score: float = 65.0,
) -> list[FacilityMatch]:
    return _search(db, query, region, limit, min_score)
