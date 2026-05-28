"""Fast in-process search (GoFundMe Algolia + DB) — no Playwright subprocess."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"


def _import_scraper():
    path = str(SCRAPER_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def run_fast_search(query: str, *, limit: int = 80) -> dict:
    """Algolia text search on GoFundMe (+ GlobalGiving if keyed). Returns campaign dicts."""
    _import_scraper()
    from live_search import search_gofundme
    from platforms.globalgiving import search_globalgiving

    merged: dict[str, dict] = {}
    by_platform: dict[str, int] = {}

    try:
        rows = await search_gofundme(query, min(limit, 200))
        by_platform["gofundme"] = len(rows)
        for row in rows:
            url = row.get("campaign_url")
            if url:
                merged[url] = row
    except Exception as exc:
        logger.error("fast search gofundme: %s", exc)

    try:
        gg = await search_globalgiving(query, max_results=min(40, limit))
        by_platform["globalgiving"] = len(gg)
        for row in gg:
            url = row.get("campaign_url")
            if url:
                merged[url] = row
    except Exception as exc:
        logger.error("fast search globalgiving: %s", exc)

    campaigns = list(merged.values())[:limit]
    return {
        "query": query,
        "campaigns": campaigns,
        "by_platform": by_platform,
        "total": len(campaigns),
        "fast": True,
    }
