"""On-demand cross-platform search — runs live_search in-process when user queries."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"
LIVE_SEARCH_TIMEOUT_SEC = int(os.getenv("LIVE_SEARCH_TIMEOUT_SEC", "90"))


def _import_scraper() -> None:
    path = str(SCRAPER_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def _persist_background(campaigns: list[dict]) -> None:
    _import_scraper()
    from live_search import _persist

    try:
        saved = await _persist(campaigns)
        logger.info("background persist saved %d campaigns", saved)
    except Exception:
        logger.exception("background persist failed")


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
    Persist runs in the background so the HTTP response returns faster.
    """
    _import_scraper()
    from live_search import run_live_search as scrape_live

    parallel = parallel or int(os.getenv("LIVE_SEARCH_PARALLEL", "10"))

    async def _run() -> dict:
        return await scrape_live(
            query,
            limit_per_platform=min(limit, 25),
            parallel=parallel,
            platforms=platforms,
        )

    try:
        summary = await asyncio.wait_for(_run(), timeout=LIVE_SEARCH_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        logger.error("live search timed out after %ss for %r", LIVE_SEARCH_TIMEOUT_SEC, query)
        return {
            "query": query,
            "campaigns": [],
            "by_platform": {},
            "total": 0,
            "error": "timeout",
        }

    if persist and summary.get("campaigns"):
        asyncio.create_task(_persist_background(summary["campaigns"]))
        summary["persist_queued"] = True

    return summary
