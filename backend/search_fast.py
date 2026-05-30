"""Fast search — APIs + HTTP HTML in parallel (target: first results < 3s)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"
FAST_HTTP_PLATFORMS = int(os.getenv("FAST_SEARCH_HTTP_PLATFORMS", "20"))
FAST_HTTP_TIMEOUT = float(os.getenv("FAST_SEARCH_HTTP_TIMEOUT_SEC", "6"))


def _import_scraper() -> None:
    path = str(SCRAPER_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


async def run_fast_search(query: str, *, limit: int = 80) -> dict:
    """Algolia + APIs + top HTTP platforms in parallel."""
    _import_scraper()
    import httpx
    from live_search import (
        API_PLATFORM_IDS,
        _search_api_platform,
        discover_search_configs,
    )
    from platforms.discover import scrape_search_http

    merged: dict[str, dict] = {}
    by_platform: dict[str, int] = {}
    per_platform = min(15, limit)

    async def api_task(pid: str) -> tuple[str, list[dict]]:
        try:
            rows = await asyncio.wait_for(
                _search_api_platform(pid, query, per_platform),
                timeout=10.0,
            )
            return pid, rows
        except Exception as exc:
            logger.error("fast search %s: %s", pid, exc)
            return pid, []

    http_configs = discover_search_configs()[:FAST_HTTP_PLATFORMS]
    priority = (
        "launchgood",
        "justgiving",
        "givebutter",
        "ketto",
        "givesendgo",
        "whydonate",
        "impactguru",
        "chuffed",
        "mightycause",
        "gogetfunding",
        "givengain",
        "fundrazr",
    )
    ordered = sorted(
        http_configs,
        key=lambda c: (priority.index(c.platform) if c.platform in priority else 99, c.platform),
    )[:FAST_HTTP_PLATFORMS]

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(FAST_HTTP_TIMEOUT, connect=4.0),
    ) as client:

        async def http_task(cfg) -> tuple[str, list[dict]]:
            try:
                rows = await asyncio.wait_for(
                    scrape_search_http(cfg, query, client=client, limit=per_platform),
                    timeout=FAST_HTTP_TIMEOUT,
                )
                return cfg.platform, rows
            except Exception:
                return cfg.platform, []

        tasks = [api_task(pid) for pid in API_PLATFORM_IDS] + [
            http_task(cfg) for cfg in ordered
        ]
        results = await asyncio.gather(*tasks)

    for platform_id, rows in results:
        by_platform[platform_id] = len(rows)
        for row in rows:
            url = row.get("campaign_url")
            if url:
                merged[url] = row

    campaigns = list(merged.values())[:limit]
    return {
        "query": query,
        "campaigns": campaigns,
        "by_platform": by_platform,
        "total": len(campaigns),
        "fast": True,
    }
