"""Fundly explore scraper."""

import logging
from typing import Optional

from playwright.async_api import ElementHandle

from platforms.base import (
    PAGES_PER_CATEGORY,
    extract_amounts_from_card,
    find_cards,
    first_text,
    new_scrape_page,
    page_delay,
)

logger = logging.getLogger(__name__)

EXPLORE_URL = "https://fundly.com/explore"

_CARD_SELECTORS = [
    "a[href*='/campaign/']",
    "[class*='campaign']",
    ".campaign-card",
    "article",
]

_TITLE_SELECTORS = ["h2", "h3", "[class*='title']", ".campaign-title"]
_SNIPPET_SELECTORS = ["p", "[class*='description']", ".campaign-description"]


async def _extract_campaign(card: ElementHandle) -> Optional[dict]:
    """Extract one Fundly campaign from a card element."""
    try:
        href = await card.get_attribute("href")
        if not href:
            link = await card.query_selector("a[href*='/campaign/']")
            href = await link.get_attribute("href") if link else None
        if not href or "/campaign/" not in href:
            return None

        campaign_url = href if href.startswith("http") else f"https://fundly.com{href}"
        title = await first_text(card, _TITLE_SELECTORS)
        story_snippet = await first_text(card, _SNIPPET_SELECTORS)

        photo_url: Optional[str] = None
        img = await card.query_selector("img")
        if img:
            photo_url = await img.get_attribute("src") or await img.get_attribute("data-src")

        raised_amount, goal_amount = await extract_amounts_from_card(card)

        category = "community"
        text = f"{title or ''} {story_snippet or ''}".lower()
        for key in ("medical", "education", "emergency"):
            if key in text:
                category = key
                break

        return {
            "title": title,
            "story_snippet": story_snippet,
            "photo_url": photo_url,
            "goal_amount": goal_amount,
            "raised_amount": raised_amount,
            "platform": "fundly",
            "campaign_url": campaign_url,
            "category": category,
            "location": None,
        }
    except Exception as exc:
        logger.error("Fundly card extraction failed: %s", exc)
        return None


async def scrape_fundly() -> list[dict]:
    """Scrape Fundly explore with pagination."""
    from playwright.async_api import async_playwright

    campaigns: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            for page_num in range(1, PAGES_PER_CATEGORY + 1):
                url = f"{EXPLORE_URL}?page={page_num}"
                logger.info("[fundly] page %d -- %s", page_num, url)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await page.wait_for_timeout(2000)
                except Exception as exc:
                    logger.error("[fundly] page %d failed: %s", page_num, exc)
                    break

                cards = await find_cards(page, _CARD_SELECTORS)
                if not cards:
                    logger.info("[fundly] page %d: empty, stopping", page_num)
                    break

                logger.info("[fundly] page %d: %d cards", page_num, len(cards))
                seen: set[str] = set()
                for card in cards:
                    campaign = await _extract_campaign(card)
                    if campaign and campaign["campaign_url"] not in seen:
                        seen.add(campaign["campaign_url"])
                        campaigns.append(campaign)

                await page_delay()
        finally:
            await page.close()
            await browser.close()

    return campaigns
