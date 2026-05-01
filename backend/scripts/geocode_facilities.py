"""Geocode every facility row that's missing lat/lng.

Strategy:
1. First, try a small offline lookup of well-known Ghanaian towns (free, instant).
2. Fall back to Nominatim (OpenStreetMap) for anything missing.
   Nominatim usage policy: 1 req/sec, custom User-Agent. Honoured here.

Usage:
    python -m scripts.geocode_facilities             # geocode rows that lack coords
    python -m scripts.geocode_facilities --reset     # re-geocode every row
"""
from __future__ import annotations

import argparse
import logging
import time
from typing import Optional

from sqlalchemy import select

from app.db.base import session_scope
from app.db.models import Facility


log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "NHIS-Assistant-School-Project/0.1 (educational use)"

# Known Ghanaian town/city centroids — covers the most-common seed values without
# any network calls. Source: OSM/Wikipedia approximations.
KNOWN_PLACES: dict[str, tuple[float, float]] = {
    "accra": (5.6037, -0.1870),
    "kumasi": (6.6885, -1.6244),
    "tamale": (9.4034, -0.8424),
    "takoradi": (4.8845, -1.7554),
    "sekondi": (4.9344, -1.7053),
    "cape coast": (5.1054, -1.2466),
    "koforidua": (6.0940, -0.2591),
    "ho": (6.6111, 0.4708),
    "sunyani": (7.3392, -2.3265),
    "bolgatanga": (10.7856, -0.8514),
    "wa": (10.0608, -2.5057),
    "tema": (5.6698, 0.0166),
    "obuasi": (6.2026, -1.6664),
    "nkawkaw": (6.5500, -0.7700),
    "techiman": (7.5919, -1.9352),
    "berekum": (7.4555, -2.5836),
    "winneba": (5.3514, -0.6233),
    "swedru": (5.5333, -0.6833),
    "kasoa": (5.5333, -0.4167),
    "mampong": (7.0667, -1.4000),
    "konongo": (6.6167, -1.2167),
    "ejura": (7.3833, -1.3667),
    "axim": (4.8689, -2.2406),
    "elmina": (5.0833, -1.3500),
    "saltpond": (5.2000, -1.0667),
    "agona swedru": (5.5333, -0.6833),
    "kintampo": (8.0500, -1.7333),
    "yendi": (9.4423, -0.0094),
    "bawku": (11.0500, -0.2333),
    "navrongo": (10.8950, -1.0925),
    "damongo": (9.0833, -1.8167),
    "salaga": (8.5500, -0.5167),
    "nkwanta": (8.2667, 0.5167),
    "hohoe": (7.1500, 0.4667),
    "kpando": (7.0167, 0.2833),
    "keta": (5.9167, 1.0000),
    "anloga": (5.7956, 0.8961),
    "aflao": (6.1167, 1.1833),
    "sogakope": (6.0017, 0.5894),
    "dunkwa": (5.9650, -1.7800),
    "tarkwa": (5.3014, -1.9939),
    "prestea": (5.4322, -2.1456),
    "bibiani": (6.4622, -2.3217),
    "goaso": (6.8000, -2.5167),
    "kenyase": (6.9333, -2.3833),
    "atebubu": (7.7500, -1.0167),
    "wenchi": (7.7333, -2.1000),
    "nalerigu": (10.5333, -0.3667),
    "gambaga": (10.5333, -0.4333),
    "tumu": (10.8833, -1.9833),
    "lawra": (10.6500, -2.9000),
    "jirapa": (10.5333, -2.7000),
}


def _key_for(town: str | None, region: str | None) -> Optional[str]:
    if not town:
        return None
    return town.strip().lower()


def _lookup_offline(town: str | None) -> Optional[tuple[float, float]]:
    key = _key_for(town, None)
    if not key:
        return None
    return KNOWN_PLACES.get(key)


def _lookup_nominatim(client, town: str, region: str | None) -> Optional[tuple[float, float]]:
    parts = [town]
    if region:
        parts.append(region)
    parts.append("Ghana")
    query = ", ".join(parts)
    try:
        r = client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "gh"},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=10.0,
        )
        r.raise_for_status()
        results = r.json()
        if not results:
            return None
        first = results[0]
        return float(first["lat"]), float(first["lon"])
    except Exception as exc:
        log.warning("Nominatim lookup failed for %r: %s", query, exc)
        return None


def geocode_all(reset: bool = False) -> tuple[int, int, int]:
    """Returns (offline_hits, network_hits, misses)."""
    import httpx  # lazy
    offline = network = misses = 0
    with httpx.Client() as client:
        with session_scope() as db:
            stmt = select(Facility)
            if not reset:
                stmt = stmt.where((Facility.lat.is_(None)) | (Facility.lng.is_(None)))
            rows = db.execute(stmt).scalars().all()
            log.info("Geocoding %d facilities", len(rows))
            for row in rows:
                coords = _lookup_offline(row.town)
                if coords:
                    row.lat, row.lng = coords
                    offline += 1
                    continue
                if not row.town:
                    misses += 1
                    continue
                coords = _lookup_nominatim(client, row.town, row.region)
                if coords:
                    row.lat, row.lng = coords
                    network += 1
                    time.sleep(1.1)  # Nominatim rate limit
                else:
                    misses += 1
    return offline, network, misses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="re-geocode rows that already have coords")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    offline, network, misses = geocode_all(reset=args.reset)
    log.info("Done — offline=%d network=%d misses=%d", offline, network, misses)


if __name__ == "__main__":
    main()
