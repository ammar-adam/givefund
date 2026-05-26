"""BackaBuddy (South Africa) — homepage/trending + news backlinks."""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from playwright.async_api import async_playwright

from platforms.base import new_scrape_page, parse_amount

logger = logging.getLogger(__name__)

PLATFORM = "backabuddy"
BASE = "https://www.backabuddy.co.za"
HOME = f"{BASE}/"
NEWS_CAMPAIGN_RE = re.compile(
    r"https?://(?:www\.)?backabuddy\.co\.za/campaign/[a-zA-Z0-9_-]+",
    re.I,
)
PATH_CAMPAIGN_RE = re.compile(r"/campaign/[a-zA-Z0-9][a-zA-Z0-9_-]+", re.I)
ZAR_RE = re.compile(r"R\s*([\d\s]+(?:\.\d+)?)", re.I)


def _parse_zar(text: str) -> Optional[float]:
    match = ZAR_RE.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def _campaign_from_url(url: str, title: str, snippet: str, raised: Optional[float]) -> dict:
    slug = url.rstrip("/").split("/")[-1]
    name = title or slug.replace("-", " ").title()
    lower = f"{name} {snippet}".lower()
    category = "community"
    if "medical" in lower or "chemo" in lower or "surgery" in lower:
        category = "medical"
    elif "education" in lower or "school" in lower:
        category = "education"
    return {
        "title": name[:200],
        "story_snippet": (snippet or "")[:500] or None,
        "photo_url": None,
        "goal_amount": None,
        "raised_amount": raised,
        "platform": PLATFORM,
        "campaign_url": url.split("?")[0],
        "category": category,
        "location": "South Africa",
    }


async def _scrape_news_links() -> list[dict]:
    """Harvest campaign URLs embedded in BackaBuddy news posts."""

    campaigns: list[dict] = []
    seen: set[str] = set()
    index_url = "https://news.backabuddy.co.za/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(index_url, headers=headers)
            resp.raise_for_status()
            urls = list(dict.fromkeys(NEWS_CAMPAIGN_RE.findall(resp.text)))
            for url in urls[:40]:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.split("/")[-1].replace("-", " ").title()
                campaigns.append(_campaign_from_url(url, slug, "Featured on BackaBuddy news.", None))
    except Exception as exc:
        logger.warning("[%s] news scrape failed: %s", PLATFORM, exc)
    return campaigns


async def _scrape_home_playwright() -> list[dict]:
    campaigns: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            await page.goto(HOME, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(5000)
            for _ in range(6):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)

            html = await page.content()
            paths = list(dict.fromkeys(PATH_CAMPAIGN_RE.findall(html)))
            for path in paths:
                url = urljoin(BASE, path)
                if url in seen:
                    continue
                seen.add(url)
                slug = path.split("/")[-1].replace("-", " ").title()
                campaigns.append(
                    _campaign_from_url(url, slug, "Trending on BackaBuddy.", None)
                )
                if len(campaigns) >= 50:
                    break
        finally:
            await page.close()
            await browser.close()

    return campaigns


async def scrape_backabuddy() -> list[dict]:
    """Scrape BackaBuddy trending/home campaigns."""

    seen: set[str] = set()
    merged: list[dict] = []
    for batch in (
        await _scrape_home_playwright(),
        await _scrape_news_links(),
    ):
        for c in batch:
            url = c["campaign_url"]
            if url in seen:
                continue
            seen.add(url)
            merged.append(c)

    logger.info("[%s] total campaigns: %d", PLATFORM, len(merged))
    return merged
