"""
Live cross-platform search — surface campaigns for any query (Palestine, cancer, etc.)

Fast path: Algolia + REST APIs in parallel.
Browser path: one shared Chromium, many tabs, link-only harvest (no per-URL enrich).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

from playwright.async_api import Browser, async_playwright

from platforms.algolia_client import AlgoliaSession
from platforms.base import new_scrape_page
from platforms.discover import DiscoverConfig, scrape_search
from platforms.globalgiving import search_globalgiving
from platforms.gofundme import _parse_algolia_hit
from registry import PlatformEntry, live_search_platforms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("live_search")

DEFAULT_LIMIT = int(os.getenv("LIVE_SEARCH_LIMIT_PER_PLATFORM", "20"))
DEFAULT_PARALLEL = int(os.getenv("LIVE_SEARCH_PARALLEL", "10"))
MAX_ALGOLIA_PAGES = int(os.getenv("LIVE_SEARCH_ALGOLIA_PAGES", "3"))
PLATFORM_TIMEOUT_SEC = float(os.getenv("LIVE_SEARCH_PLATFORM_TIMEOUT_SEC", "22"))


async def _ensure_algolia(session: AlgoliaSession, query: str) -> None:
    if session.ready():
        return
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        session.attach(page)
        try:
            from urllib.parse import quote

            await page.goto(
                f"https://www.gofundme.com/s?q={quote(query)}",
                wait_until="domcontentloaded",
                timeout=45_000,
            )
            await page.wait_for_timeout(2500)
        finally:
            await page.close()
            await browser.close()


async def search_gofundme(query: str, limit: int) -> list[dict]:
    session = AlgoliaSession()
    if not session.ready():
        await _ensure_algolia(session, query)
    if not session.ready():
        logger.warning("[gofundme] no Algolia credentials for live search")
        return []

    hits = await session.search_text(
        query, max_pages=MAX_ALGOLIA_PAGES, hits_per_page=min(50, limit)
    )
    campaigns: list[dict] = []
    for hit in hits:
        row = _parse_algolia_hit(hit, "community")
        if row:
            campaigns.append(row)
        if len(campaigns) >= limit:
            break
    return campaigns


def _entry_to_discover_config(entry: PlatformEntry) -> DiscoverConfig | None:
    if not entry.search_url_template or not entry.base_url:
        return None
    start_urls = entry.discover_urls or (entry.base_url,)
    markers = entry.link_markers or ("/campaign/",)
    return DiscoverConfig(
        platform=entry.id,
        base_url=entry.base_url,
        start_urls=start_urls,
        link_markers=markers,
        search_url_template=entry.search_url_template,
        max_campaigns=min(DEFAULT_LIMIT, 30),
    )


async def _search_opencollective(query: str, limit: int) -> list[dict]:
    from platforms.opencollective import search_opencollective

    return await search_opencollective(query, max_results=limit)


async def _search_platform_entry(
    entry: PlatformEntry,
    query: str,
    limit: int,
    *,
    browser: Browser | None = None,
) -> list[dict]:
    try:
        if entry.scrape_method == "algolia":
            return await search_gofundme(query, limit)
        if entry.id == "globalgiving" or (
            entry.scrape_method == "official_api" and entry.id == "globalgiving"
        ):
            return await search_globalgiving(query, max_results=limit)
        if entry.id == "opencollective":
            return await _search_opencollective(query, limit)
        cfg = _entry_to_discover_config(entry)
        if cfg and browser is not None:
            return await scrape_search(cfg, query, browser=browser, enrich=False, limit=limit)
        if cfg:
            return await scrape_search(cfg, query, enrich=False, limit=limit)
    except Exception as exc:
        logger.error("[%s] live search error: %s", entry.id, exc)
    return []


async def _search_with_timeout(
    entry: PlatformEntry,
    query: str,
    limit: int,
    *,
    browser: Browser | None,
    sem: asyncio.Semaphore,
) -> tuple[str, list[dict]]:
    async with sem:
        try:
            rows = await asyncio.wait_for(
                _search_platform_entry(entry, query, limit, browser=browser),
                timeout=PLATFORM_TIMEOUT_SEC,
            )
            return entry.id, rows
        except asyncio.TimeoutError:
            logger.warning("[%s] live search timed out after %.0fs", entry.id, PLATFORM_TIMEOUT_SEC)
            return entry.id, []
        except Exception as exc:
            logger.error("[%s] live search failed: %s", entry.id, exc)
            return entry.id, []


async def run_live_search(
    query: str,
    *,
    limit_per_platform: int = DEFAULT_LIMIT,
    parallel: int = DEFAULT_PARALLEL,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Fan out a search query across all configured platforms in parallel."""
    query = query.strip()
    if len(query) < 2:
        return {"query": query, "campaigns": [], "by_platform": {}, "total": 0}

    entries = live_search_platforms()
    if platforms:
        allow = set(platforms)
        entries = [e for e in entries if e.id in allow]

    api_entries = [
        e
        for e in entries
        if e.scrape_method in ("algolia", "official_api")
        or e.id in ("globalgiving", "opencollective")
    ]
    browser_entries = [
        e
        for e in entries
        if e not in api_entries and e.search_url_template
    ]

    by_platform: dict[str, int] = {}
    merged: dict[str, dict] = {}
    sem = asyncio.Semaphore(max(1, parallel))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            tasks = [
                _search_with_timeout(e, query, limit_per_platform, browser=browser, sem=sem)
                for e in api_entries
            ] + [
                _search_with_timeout(e, query, limit_per_platform, browser=browser, sem=sem)
                for e in browser_entries
            ]
            results = await asyncio.gather(*tasks)
            for platform_id, rows in results:
                by_platform[platform_id] = len(rows)
                for row in rows:
                    url = row.get("campaign_url")
                    if url:
                        merged[url] = row
        finally:
            await browser.close()

    campaigns = list(merged.values())
    logger.info(
        "live search %r -> %d unique (%s)",
        query,
        len(campaigns),
        ", ".join(f"{k}:{v}" for k, v in sorted(by_platform.items()) if v),
    )
    return {
        "query": query,
        "campaigns": campaigns,
        "by_platform": by_platform,
        "total": len(campaigns),
        "live": True,
    }


async def _persist(campaigns: list[dict]) -> int:
    from db import create_table, get_connection, persist_campaigns_batch

    async with get_connection() as conn:
        await create_table(conn)
        return await persist_campaigns_batch(conn, campaigns)


def main() -> None:
    parser = argparse.ArgumentParser(description="Live cross-platform campaign search")
    parser.add_argument("--q", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL)
    parser.add_argument("--platforms", nargs="*", help="Subset of platform ids")
    parser.add_argument("--persist", action="store_true", help="Upsert results into DB")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    summary = asyncio.run(
        run_live_search(
            args.q,
            limit_per_platform=args.limit,
            parallel=args.parallel,
            platforms=args.platforms,
        )
    )
    if args.persist and summary["campaigns"]:
        saved = asyncio.run(_persist(summary["campaigns"]))
        summary["saved"] = saved

    if args.json:
        print(json.dumps(summary, default=str))
    else:
        print(f"query={summary['query']} total={summary['total']} saved={summary.get('saved')}")


if __name__ == "__main__":
    main()
