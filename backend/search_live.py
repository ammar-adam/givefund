"""On-demand cross-platform search — runs live_search in-process when user queries."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"
LIVE_SEARCH_TIMEOUT_SEC = int(os.getenv("LIVE_SEARCH_TIMEOUT_SEC", "180"))


def _import_scraper() -> None:
    path = str(SCRAPER_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def run_live_search(
    query: str,
    *,
    limit: int = 50,
    parallel: int | None = None,
    platforms: list[str] | None = None,
    persist: bool = False,
) -> dict:
    """
    Scrape/search all wired platforms for this query (Playwright + Algolia).
    Optionally upsert hits into givefund.db so Give Now uses real campaign ids.
    """
    _import_scraper()
    from live_search import _persist, run_live_search as scrape_live

    parallel = parallel or int(os.getenv("LIVE_SEARCH_PARALLEL", "5"))

    async def _run() -> dict:
        summary = await scrape_live(
            query,
            limit_per_platform=limit,
            parallel=parallel,
            platforms=platforms,
        )
        if persist and summary.get("campaigns"):
            summary["saved"] = await _persist(summary["campaigns"])
        return summary

    try:
        return await asyncio.wait_for(_run(), timeout=LIVE_SEARCH_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        logger.error("live search timed out after %ss for %r", LIVE_SEARCH_TIMEOUT_SEC, query)
        return {
            "query": query,
            "campaigns": [],
            "by_platform": {},
            "total": 0,
            "error": "timeout",
        }
