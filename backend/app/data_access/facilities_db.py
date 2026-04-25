"""Accredited facilities lookup backed by a CSV directory."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

from app.config import settings


@dataclass
class FacilityMatch:
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


def _yes(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"yes", "true", "1", "y"}


def _split_services(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    path = Path(settings.facilities_csv)
    if not path.exists():
        raise FileNotFoundError(f"Facilities CSV not found at {path}")
    df = pd.read_csv(path)
    required = {"name", "type", "region", "accredited"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Facilities CSV missing columns: {missing}")
    return df


def _row_to_match(row: pd.Series, score: float) -> FacilityMatch:
    return FacilityMatch(
        name=str(row.get("name", "")),
        type=str(row.get("type", "")),
        region=str(row.get("region", "")),
        district=str(row.get("district", "")),
        town=str(row.get("town", "")),
        accredited=_yes(row.get("accredited")),
        accreditation_status=str(row.get("accreditation_status", "")),
        services=_split_services(row.get("services")),
        phone=str(row.get("phone", "")),
        score=score,
    )


def search_facility(
    query: str,
    region: str | None = None,
    limit: int = 5,
    min_score: float = 65.0,
) -> list[FacilityMatch]:
    df = _load_dataframe()
    if df.empty or not query.strip():
        return []

    if region:
        df = df[df["region"].str.lower() == region.strip().lower()]

    candidates: list[tuple[int, float]] = []
    for idx, row in df.iterrows():
        haystacks = [
            str(row.get("name", "")),
            str(row.get("town", "")),
            str(row.get("district", "")),
        ]
        best = max((fuzz.WRatio(query, h) for h in haystacks if h), default=0)
        if best >= min_score:
            candidates.append((idx, float(best)))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [_row_to_match(df.loc[idx], score) for idx, score in candidates[:limit]]


def list_facilities_by_region(region: str) -> list[dict]:
    df = _load_dataframe()
    filtered = df[df["region"].str.lower() == region.strip().lower()]
    return filtered.to_dict(orient="records")


def reload_cache() -> None:
    _load_dataframe.cache_clear()
