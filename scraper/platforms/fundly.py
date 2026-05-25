"""Fundly scraper — fundly.com redirects to SignUpGenius; scrape public Fundly listings where available."""

import logging
import re
from typing import Optional

from playwright.async_api import async_playwright

from platforms.base import new_scrape_page, parse_amount

logger = logging.getLogger(__name__)

# Fundly's explore URL redirects; try campaign search pages on signupgenius fundly hub
CANDIDATE_URLS = [
    "https://fundly.com/p/campaigns",
    "https://fundly.com/campaign/browse",
]


async def _extract_from_page(page, source_url: str) -> list[dict]:
    """Pull campaign-like links and minimal fields from the current page."""
    html = await page.content()
    # Fundly campaign URLs historically: /campaigns/slug or fundly.com/c/slug
    patterns = [
        r'href="(https?://(?:www\.)?fundly\.com/campaigns/[^"]+)"',
        r'href="(https?://(?:www\.)?fundly\.com/c/[^"]+)"',
        r'href="(/campaigns/[^"]+)"',
    ]
    urls: set[str] = set()
    for pat in patterns:
        for match in re.findall(pat, html):
            full = match if match.startswith("http") else f"https://fundly.com{match}"
            urls.add(full.split("?")[0])

    campaigns: list[dict] = []
    for url in list(urls)[:30]:
        slug = url.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title()
        campaigns.append({
            "title": title,
            "story_snippet": None,
            "photo_url": None,
            "goal_amount": None,
            "raised_amount": None,
            "platform": "fundly",
            "campaign_url": url,
            "category": "community",
            "location": None,
        })
    if campaigns:
        logger.info("[fundly] extracted %d links from %s", len(campaigns), source_url)
    return campaigns


async def scrape_fundly() -> list[dict]:
    """Attempt Fundly scrape; returns empty list if site has no public listings."""
    all_campaigns: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            for url in CANDIDATE_URLS:
                try:
                    logger.info("[fundly] trying %s", url)
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
                    final = page.url
                    if "signupgenius" in final and "fundly" not in final.lower():
                        logger.warning("[fundly] %s redirected to %s — no listings", url, final)
                        continue
                    found = await _extract_from_page(page, url)
                    all_campaigns.extend(found)
                    if found:
                        break
                except Exception as exc:
                    logger.error("[fundly] %s failed: %s", url, exc)
        finally:
            await page.close()
            await browser.close()

    if not all_campaigns:
        logger.warning(
            "[fundly] no campaigns found — fundly.com no longer hosts a public explore page. "
            "Fundly campaigns are omitted until a stable listing URL exists."
        )
    return all_campaigns
