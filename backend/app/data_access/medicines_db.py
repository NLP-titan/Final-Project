"""Medicines lookup backed by a CSV formulary."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from app.config import settings


@dataclass
class MedicineMatch:
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
        d = asdict(self)
        return d


def _yes(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"yes", "true", "1", "y"}


def _split_levels(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [v.strip() for v in str(value).split(";") if v.strip()]


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    path = Path(settings.medicines_csv)
    if not path.exists():
        raise FileNotFoundError(f"Medicines CSV not found at {path}")
    df = pd.read_csv(path)
    required = {"name", "generic_name", "strength", "form", "covered"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Medicines CSV missing columns: {missing}")
    return df


def _row_to_match(row: pd.Series, score: float) -> MedicineMatch:
    return MedicineMatch(
        name=str(row.get("name", "")),
        generic_name=str(row.get("generic_name", "")),
        strength=str(row.get("strength", "")),
        form=str(row.get("form", "")),
        therapeutic_class=str(row.get("therapeutic_class", "")),
        covered=_yes(row.get("covered")),
        level_of_care=_split_levels(row.get("level_of_care")),
        notes=str(row.get("notes", "")),
        score=score,
    )


def search_medicine(query: str, limit: int = 5, min_score: float = 60.0) -> list[MedicineMatch]:
    """Fuzzy search the formulary by brand or generic name.

    Returns up to `limit` matches sorted by score. Both brand and generic name are scored
    against the query and the higher of the two is used.
    """
    df = _load_dataframe()
    if df.empty or not query.strip():
        return []

    candidates = []
    for idx, row in df.iterrows():
        haystacks = [str(row.get("name", "")), str(row.get("generic_name", ""))]
        best = max(
            (fuzz.WRatio(query, h) for h in haystacks if h),
            default=0,
        )
        if best >= min_score:
            candidates.append((idx, float(best)))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [_row_to_match(df.loc[idx], score) for idx, score in candidates[:limit]]


def list_medicines() -> list[dict]:
    df = _load_dataframe()
    return df.to_dict(orient="records")


def reload_cache() -> None:
    _load_dataframe.cache_clear()
