"""Scrape health news from Ghana Health Service and a Ghana mainstream news outlet.

Sources:
  - Ghana Health Service (`https://www.ghs.gov.gh/news-and-events`) — official
    news. Server-rendered HTML; we read each `<article>` block.
  - MyJoyOnline Health (`https://www.myjoyonline.com/news/health/feed/`) — RSS
    feed from a major Ghana news outlet. Picked over Ghanaweb because Ghanaweb
    runs a JavaScript anti-bot challenge wall ("Challenge Validation") that
    can't be defeated without a headless browser. MyJoyOnline serves clean
    RSS over plain HTTP and is a reliable signal for nationwide health news.

Each source is wrapped in a try/except — one site failing won't block the
others. Rows are deduped by `source_url` (UNIQUE on `HealthUpdate.source_url`).

Run on demand via `POST /api/health-updates/refresh` (admin) or as a background
job (`scripts/refresh_health_updates.py`).
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urljoin

from sqlalchemy import select

from app.db.base import session_scope
from app.db.models import HealthUpdate


log = logging.getLogger(__name__)


GHS_LISTING_URL = "https://www.ghs.gov.gh/news-and-events"
MYJOY_FEED_URL = "https://www.myjoyonline.com/news/health/feed/"
GHANAWEB_LISTING_URL = "https://www.ghanaweb.com/GhanaHomePage/health/"

# Looks like a normal browser; news sites 403 default httpx headers.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

REQUEST_TIMEOUT = 15.0


@dataclass
class ScrapedItem:
    title: str
    source: str
    source_url: str
    summary: Optional[str] = None
    category: Optional[str] = None
    published_date: Optional[str] = None


def _fetch(url: str) -> Optional[str]:
    import httpx  # lazy — keep module importable in environments without httpx
    try:
        with httpx.Client(headers=_HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.text
    except httpx.HTTPStatusError as exc:
        log.warning("Scraper got HTTP %s from %s", exc.response.status_code, url)
    except Exception as exc:
        log.warning("Scraper request failed for %s: %s", url, exc)
    return None


def _parse_html(html: str):
    from bs4 import BeautifulSoup  # lazy — only loaded when scraping is invoked
    return BeautifulSoup(html, "lxml")


def _is_challenge_page(html: str) -> bool:
    """Some sites (e.g. ghanaweb) gate behind a JS proof-of-work; the
    response is a tiny HTML stub with 'Challenge Validation' in the title."""
    if not html or len(html) > 5000:
        return False
    return "challenge validation" in html.lower() or "sec-text-if" in html


# ---------------------------------------------------------------------------
# Ghana Health Service — HTML scrape of <article> blocks
# ---------------------------------------------------------------------------
def scrape_ghs(limit: int = 10) -> list[ScrapedItem]:
    html = _fetch(GHS_LISTING_URL)
    if not html:
        return []
    soup = _parse_html(html)
    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for art in soup.find_all("article"):
        # title — the first <h1>/<h2>/<h3> inside the card
        h = art.find(["h1", "h2", "h3", "h4"])
        title = " ".join(h.get_text(" ", strip=True).split()) if h else ""
        if not title or len(title.split()) < 3:
            continue

        # link — first <a> with /news-and-events/<slug>
        link = None
        for a in art.find_all("a", href=True):
            href = a["href"].strip()
            if "/news-and-events/" in href and not href.rstrip("/").endswith("/news-and-events"):
                link = urljoin(GHS_LISTING_URL, href)
                break
        if not link or link in seen:
            continue
        seen.add(link)

        # summary — first <p>
        p = art.find("p")
        summary = " ".join(p.get_text(" ", strip=True).split())[:500] if p else None

        # date — first <time> or anything that looks like a date
        time_el = art.find("time")
        published = (
            " ".join(time_el.get_text(" ", strip=True).split()) if time_el else None
        )

        items.append(
            ScrapedItem(
                title=title[:500],
                source="Ghana Health Service",
                source_url=link,
                summary=summary,
                category=_infer_category(title + " " + (summary or "")),
                published_date=published,
            )
        )
        if len(items) >= limit:
            break

    log.info("GHS scrape: %d item(s)", len(items))
    return items


# ---------------------------------------------------------------------------
# MyJoyOnline Health — RSS feed
# ---------------------------------------------------------------------------
_RSS_DATE_RE = re.compile(r",\s*(\d{1,2}\s+\w+\s+\d{4})")


def _format_rss_date(raw: Optional[str]) -> Optional[str]:
    """RFC-822 date like 'Fri, 01 May 2026 12:15:13 +0000' → '01 May 2026'."""
    if not raw:
        return None
    m = _RSS_DATE_RE.search(raw)
    return m.group(1) if m else raw


def scrape_myjoy(limit: int = 10) -> list[ScrapedItem]:
    body = _fetch(MYJOY_FEED_URL)
    if not body:
        return []
    items: list[ScrapedItem] = []
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        log.warning("MyJoyOnline RSS parse error: %s", exc)
        return []

    # RSS 2.0: rss > channel > item
    channel = root.find("channel")
    if channel is None:
        return []
    seen: set[str] = set()
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        date_el = item.find("pubDate")
        desc_el = item.find("description")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        if not title or not link or link in seen:
            continue
        seen.add(link)
        # Strip HTML from description for a clean summary.
        raw_desc = (desc_el.text if desc_el is not None else "") or ""
        summary = re.sub(r"<[^>]+>", " ", raw_desc)
        summary = " ".join(summary.split())[:500] or None
        items.append(
            ScrapedItem(
                title=title[:500],
                source="MyJoyOnline Health",
                source_url=link,
                summary=summary,
                category=_infer_category(title + " " + (summary or "")),
                published_date=_format_rss_date(date_el.text if date_el is not None else None),
            )
        )
        if len(items) >= limit:
            break
    log.info("MyJoyOnline scrape: %d item(s)", len(items))
    return items


# ---------------------------------------------------------------------------
# Ghanaweb — best effort. The site gates behind a JS proof-of-work challenge
# that we can't solve without a headless browser, so this normally returns 0.
# Kept as a hook for the day they remove the wall (or someone runs us through
# a residential proxy).
# ---------------------------------------------------------------------------
def scrape_ghanaweb(limit: int = 10) -> list[ScrapedItem]:
    html = _fetch(GHANAWEB_LISTING_URL)
    if not html:
        return []
    if _is_challenge_page(html):
        log.info("Ghanaweb returned a JS challenge page — skipping")
        return []
    soup = _parse_html(html)
    items: list[ScrapedItem] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/GhanaHomePage/" not in href:
            continue
        if href.endswith("/health/") or "/health/index" in href:
            continue
        if "/Photos" in href or "/video" in href.lower():
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title or len(title.split()) < 5:
            continue
        full_url = urljoin(GHANAWEB_LISTING_URL, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        items.append(
            ScrapedItem(
                title=title[:500],
                source="GhanaWeb Health",
                source_url=full_url,
                summary=None,
                category=_infer_category(title),
                published_date=None,
            )
        )
        if len(items) >= limit:
            break
    log.info("Ghanaweb scrape: %d item(s)", len(items))
    return items


# ---------------------------------------------------------------------------
# Categorisation heuristic — keep cheap, no LLM
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Drug Formulary", ("drug", "medicine", "formulary", "pharmacy", "prescription")),
    ("Disease Alerts", ("outbreak", "cholera", "malaria", "covid", "polio", "vaccin", "alert", "epidemic", "ebola", "tuberculos", "dengue", "lassa")),
    ("Policy Updates", ("nhis", "policy", "premium", "renew", "card", "regulation", "announce", "minister", "free primary")),
]


def _infer_category(text: str) -> str:
    lower = text.lower()
    for label, keywords in _CATEGORY_KEYWORDS:
        if any(k in lower for k in keywords):
            return label
    return "General Health"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def persist(items: Iterable[ScrapedItem]) -> int:
    """Insert items by source_url; skip ones that already exist."""
    inserted = 0
    with session_scope() as db:
        existing_urls = {
            row[0]
            for row in db.execute(
                select(HealthUpdate.source_url).where(HealthUpdate.source_url.is_not(None))
            ).all()
        }
        for it in items:
            if not it.source_url or it.source_url in existing_urls:
                continue
            db.add(
                HealthUpdate(
                    title=it.title,
                    source=it.source,
                    source_url=it.source_url,
                    category=it.category,
                    summary=it.summary,
                    published_date=it.published_date,
                )
            )
            existing_urls.add(it.source_url)
            inserted += 1
    return inserted


def refresh_all(limit_per_source: int = 10) -> dict:
    ghs = scrape_ghs(limit=limit_per_source)
    myjoy = scrape_myjoy(limit=limit_per_source)
    ghw = scrape_ghanaweb(limit=limit_per_source)
    inserted = persist(ghs + myjoy + ghw)
    return {
        "ghs_found": len(ghs),
        "myjoy_found": len(myjoy),
        "ghanaweb_found": len(ghw),
        "inserted": inserted,
    }
