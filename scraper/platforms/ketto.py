"""Ketto (India) — sitemap + Playwright discover."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from platforms.base import new_scrape_page, parse_amount
from platforms.sitemap_util import fetch_sitemap_locs, filter_urls

logger = logging.getLogger(__name__)

PLATFORM = "ketto"
FUNDRAISER_MARKERS = ("/fundraiser/", "/crowdfunding/")
SITEMAP_CANDIDATES = (
    "https://www.ketto.org/sitemap.xml",
    "https://www.ketto.org/sitemap_index.xml",
    "https://www.ketto.org/sitemap-fundraiser.xml",
)
BROWSE_URLS = (
    "https://www.ketto.org/crowdfunding/fundraisers",
    "https://www.ketto.org/medical-fundraising",
    "https://www.ketto.org/browsefundraiser",
)


def _category(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ("medical", "cancer", "hospital", "surgery")):
        return "medical"
    if "education" in lower:
        return "education"
    if any(w in lower for w in ("flood", "earthquake", "emergency")):
        return "emergency"
    return "community"


def _campaign_from_url(url: str, meta: dict[str, Any]) -> dict:
    title = (meta.get("title") or "").strip()
    if not title:
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title()
    story = (meta.get("story") or meta.get("description") or "")[:500]
    return {
        "title": title[:200],
        "story_snippet": story or None,
        "photo_url": meta.get("image"),
        "goal_amount": meta.get("goal"),
        "raised_amount": meta.get("raised"),
        "platform": PLATFORM,
        "campaign_url": url.split("?")[0],
        "category": _category(f"{title} {story}"),
        "location": "India",
    }


async def _urls_from_sitemaps() -> list[str]:
    urls: list[str] = []
    for sm in SITEMAP_CANDIDATES:
        locs = await fetch_sitemap_locs(sm, max_locs=300)
        found = filter_urls(locs, *FUNDRAISER_MARKERS)
        urls.extend(found)
        if found:
            logger.info("[%s] sitemap %s → %d urls", PLATFORM, sm, len(found))
    return list(dict.fromkeys(urls))[:80]


async def _urls_from_playwright() -> list[str]:
    found: set[str] = set()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await new_scrape_page(browser)
        try:
            for start in BROWSE_URLS:
                try:
                    await page.goto(start, wait_until="domcontentloaded", timeout=90_000)
                    await page.wait_for_timeout(4000)
                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500)
                    hrefs = await page.eval_on_selector_all(
                        "a[href]",
                        """els => [...new Set(els.map(e => e.href.split('?')[0]))]""",
                    )
                    for h in hrefs:
                        if any(m in h for m in FUNDRAISER_MARKERS) and "ketto.org" in h:
                            found.add(h)
                except Exception as exc:
                    logger.warning("[%s] browse failed %s: %s", PLATFORM, start, exc)
        finally:
            await page.close()
            await browser.close()
    return list(found)[:60]


async def _enrich(page, url: str) -> Optional[dict]:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(2000)
        meta = await page.evaluate("""() => {
          const og = (k) => document.querySelector(`meta[property="og:${k}"]`)?.content;
          return {
            title: og('title') || document.querySelector('h1')?.innerText,
            description: og('description'),
            image: og('image'),
          };
        }""")
        body = (await page.inner_text("body"))[:6000]
        inr = [
            parse_amount(m.replace("₹", "").replace("Rs", "").replace("rs", ""))
            for m in re.findall(r"₹\s*[\d,\.]+[kKmM]?", body)
        ]
        inr = [x for x in inr if x]
        raised = inr[0] if inr else None
        goal = inr[1] if len(inr) > 1 else None
        meta["raised"] = raised
        meta["goal"] = goal
        meta["story"] = meta.get("description")
        return _campaign_from_url(url, meta)
    except Exception as exc:
        logger.debug("[%s] enrich %s: %s", PLATFORM, url, exc)
        return None


async def scrape_ketto() -> list[dict]:
    urls = await _urls_from_sitemaps()
    if len(urls) < 5:
        urls = list(dict.fromkeys([*urls, *(await _urls_from_playwright())]))[:80]

    if not urls:
        logger.warning("[%s] no campaign URLs discovered", PLATFORM)
        return []

    campaigns: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            for i, url in enumerate(urls[:40]):
                c = await _enrich(page, url)
                if c:
                    campaigns.append(c)
                if not c:
                    campaigns.append(_campaign_from_url(url, {}))
                if (i + 1) % 10 == 0:
                    logger.info("[%s] enriched %d/%d", PLATFORM, i + 1, len(urls))
        finally:
            await page.close()
            await browser.close()

    logger.info("[%s] total campaigns: %d", PLATFORM, len(campaigns))
    return campaigns
