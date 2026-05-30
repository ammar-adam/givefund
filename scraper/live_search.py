"""
Live cross-platform search — HTTP-first (sub-10s target), optional Playwright fallback.

Tier 1: Algolia + REST APIs (1–3s)
Tier 2: HTTP HTML harvest for all platforms with search URLs (~5–8s parallel)
Tier 3: Playwright fallback only for empty HTTP (optional, slower)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections.abc import AsyncIterator
from typing import Any

import httpx
from playwright.async_api import Browser, async_playwright

from platforms.algolia_client import AlgoliaSession
from platforms.base import new_scrape_page
from platforms.discover import DiscoverConfig, scrape_search, scrape_search_http
from platforms.extra import EXTRA_CONFIGS
from platforms.globalgiving import search_globalgiving
from platforms.gofundme import _parse_algolia_hit
from registry import PlatformEntry, live_search_platforms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("live_search")

DEFAULT_LIMIT = int(os.getenv("LIVE_SEARCH_LIMIT_PER_PLATFORM", "15"))
DEFAULT_PARALLEL = int(os.getenv("LIVE_SEARCH_PARALLEL", "25"))
MAX_ALGOLIA_PAGES = int(os.getenv("LIVE_SEARCH_ALGOLIA_PAGES", "2"))
HTTP_TIMEOUT_SEC = float(os.getenv("LIVE_SEARCH_HTTP_TIMEOUT_SEC", "8"))
API_TIMEOUT_SEC = float(os.getenv("LIVE_SEARCH_API_TIMEOUT_SEC", "12"))
PW_TIMEOUT_SEC = float(os.getenv("LIVE_SEARCH_PW_TIMEOUT_SEC", "18"))
PW_FALLBACK = os.getenv("LIVE_SEARCH_PLAYWRIGHT_FALLBACK", "true").lower() in (
    "1",
    "true",
    "yes",
)
MAX_PW_FALLBACK = int(os.getenv("LIVE_SEARCH_MAX_PW_FALLBACK", "8"))


def discover_search_configs() -> list[DiscoverConfig]:
    """All platforms with search URLs: extra.py + registry entries."""
    configs = [c for c in EXTRA_CONFIGS if c.search_url_template]
    seen = {c.platform for c in configs}

    for entry in live_search_platforms():
        if entry.id in seen or entry.id in API_PLATFORM_IDS:
            continue
        if not entry.search_url_template or not entry.base_url:
            continue
        markers = entry.link_markers or ("/campaign/",)
        configs.append(
            DiscoverConfig(
                platform=entry.id,
                base_url=entry.base_url,
                start_urls=entry.discover_urls or (entry.base_url,),
                link_markers=markers,
                search_url_template=entry.search_url_template,
                max_campaigns=min(DEFAULT_LIMIT, 25),
            )
        )
        seen.add(entry.id)
    return configs


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
                timeout=30_000,
            )
            await page.wait_for_timeout(2000)
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


async def _search_opencollective(query: str, limit: int) -> list[dict]:
    from platforms.opencollective import search_opencollective

    return await search_opencollective(query, max_results=limit)


async def _search_api_platform(platform_id: str, query: str, limit: int) -> list[dict]:
    if platform_id == "gofundme":
        return await search_gofundme(query, limit)
    if platform_id == "globalgiving":
        return await search_globalgiving(query, max_results=limit)
    if platform_id == "opencollective":
        return await _search_opencollective(query, limit)
    return []


API_PLATFORM_IDS = ("gofundme", "globalgiving", "opencollective")


async def _search_http_config(
    config: DiscoverConfig,
    query: str,
    limit: int,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> tuple[str, list[dict]]:
    async with sem:
        try:
            rows = await asyncio.wait_for(
                scrape_search_http(config, query, client=client, limit=limit),
                timeout=HTTP_TIMEOUT_SEC,
            )
            return config.platform, rows
        except asyncio.TimeoutError:
            return config.platform, []
        except Exception as exc:
            logger.debug("[%s] http search: %s", config.platform, exc)
            return config.platform, []


async def _search_pw_config(
    config: DiscoverConfig,
    query: str,
    limit: int,
    browser: Browser,
    sem: asyncio.Semaphore,
) -> tuple[str, list[dict]]:
    async with sem:
        try:
            rows = await asyncio.wait_for(
                scrape_search(config, query, browser=browser, enrich=False, limit=limit),
                timeout=PW_TIMEOUT_SEC,
            )
            return config.platform, rows
        except asyncio.TimeoutError:
            return config.platform, []
        except Exception as exc:
            logger.debug("[%s] pw fallback: %s", config.platform, exc)
            return config.platform, []


def _merge_rows(
    merged: dict[str, dict],
    by_platform: dict[str, int],
    platform_id: str,
    rows: list[dict],
) -> list[dict]:
    """Merge rows into merged dict; return new campaigns for streaming."""
    by_platform[platform_id] = len(rows)
    new: list[dict] = []
    for row in rows:
        url = row.get("campaign_url")
        if url and url not in merged:
            merged[url] = row
            new.append(row)
    return new


async def run_live_search_stream(
    query: str,
    *,
    limit_per_platform: int = DEFAULT_LIMIT,
    parallel: int = DEFAULT_PARALLEL,
    platforms: list[str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yield search progress events for SSE:
    - platform: {platform, campaigns, count, total_so_far}
    - done: {campaigns, by_platform, total}
    """
    query = query.strip()
    if len(query) < 2:
        yield {"type": "done", "query": query, "campaigns": [], "by_platform": {}, "total": 0}
        return

    allow = set(platforms) if platforms else None
    http_configs = [
        c for c in discover_search_configs() if not allow or c.platform in allow
    ]
    api_ids = [p for p in API_PLATFORM_IDS if not allow or p in allow]

    by_platform: dict[str, int] = {}
    merged: dict[str, dict] = {}
    sem = asyncio.Semaphore(max(1, parallel))
    limit = min(limit_per_platform, 20)

    async def run_api(pid: str) -> tuple[str, list[dict]]:
        async with sem:
            try:
                rows = await asyncio.wait_for(
                    _search_api_platform(pid, query, limit),
                    timeout=API_TIMEOUT_SEC,
                )
                return pid, rows
            except Exception:
                return pid, []

    api_tasks = [asyncio.create_task(run_api(pid)) for pid in api_ids]

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(HTTP_TIMEOUT_SEC, connect=5.0),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    ) as client:
        http_tasks = {
            cfg.platform: asyncio.create_task(
                _search_http_config(cfg, query, limit, client, sem)
            )
            for cfg in http_configs
        }

        pending = {t: pid for pid, t in zip(api_ids, api_tasks)}
        pending.update({t: pid for pid, t in http_tasks.items()})

        http_empty: list[DiscoverConfig] = []

        while pending:
            done, _ = await asyncio.wait(pending.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                platform_id = pending.pop(task)
                try:
                    pid, rows = task.result()
                except Exception:
                    pid, rows = platform_id, []

                new_rows = _merge_rows(merged, by_platform, pid, rows)
                if new_rows:
                    yield {
                        "type": "platform",
                        "platform": pid,
                        "campaigns": new_rows,
                        "count": len(rows),
                        "total_so_far": len(merged),
                    }

                if (
                    PW_FALLBACK
                    and pid not in API_PLATFORM_IDS
                    and len(rows) == 0
                ):
                    cfg = next((c for c in http_configs if c.platform == pid), None)
                    if cfg:
                        http_empty.append(cfg)

    if PW_FALLBACK and http_empty:
        fallback_configs = http_empty[:MAX_PW_FALLBACK]
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                pw_sem = asyncio.Semaphore(4)
                pw_tasks = [
                    asyncio.create_task(
                        _search_pw_config(cfg, query, limit, browser, pw_sem)
                    )
                    for cfg in fallback_configs
                ]
                for task in asyncio.as_completed(pw_tasks):
                    pid, rows = await task
                    new_rows = _merge_rows(merged, by_platform, pid, rows)
                    if new_rows:
                        yield {
                            "type": "platform",
                            "platform": pid,
                            "campaigns": new_rows,
                            "count": len(rows),
                            "total_so_far": len(merged),
                            "fallback": "playwright",
                        }
            finally:
                await browser.close()

    campaigns = list(merged.values())
    yield {
        "type": "done",
        "query": query,
        "campaigns": campaigns,
        "by_platform": by_platform,
        "total": len(campaigns),
        "live": True,
    }


async def run_live_search(
    query: str,
    *,
    limit_per_platform: int = DEFAULT_LIMIT,
    parallel: int = DEFAULT_PARALLEL,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Collect full search result (uses streaming internally)."""
    result: dict[str, Any] = {
        "query": query,
        "campaigns": [],
        "by_platform": {},
        "total": 0,
    }
    async for event in run_live_search_stream(
        query,
        limit_per_platform=limit_per_platform,
        parallel=parallel,
        platforms=platforms,
    ):
        if event.get("type") == "done":
            result = event
    logger.info(
        "live search %r -> %d (%s)",
        query,
        result.get("total", 0),
        ", ".join(f"{k}:{v}" for k, v in sorted((result.get("by_platform") or {}).items()) if v),
    )
    return result


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
