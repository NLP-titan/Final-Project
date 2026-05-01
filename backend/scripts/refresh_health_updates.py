"""Scrape GHS + GhanaWeb and store new posts in the health_updates table.

Designed to be run from cron / a scheduler. Idempotent — duplicates are skipped
by `source_url`.

Usage:
    python -m scripts.refresh_health_updates
    python -m scripts.refresh_health_updates --limit 20
"""
from __future__ import annotations

import argparse
import logging

from app.services.health_updates_scraper import refresh_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Items per source")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    result = refresh_all(limit_per_source=args.limit)
    print(
        f"GHS={result['ghs_found']} MyJoy={result.get('myjoy_found', 0)} "
        f"Ghanaweb={result['ghanaweb_found']} Inserted={result['inserted']}"
    )


if __name__ == "__main__":
    main()
