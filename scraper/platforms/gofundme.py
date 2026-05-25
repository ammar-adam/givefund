"""GoFundMe discover scraper."""

import asyncio
import logging
from typing import Optional

from playwright.async_api import Browser, ElementHandle, Page

from platforms.base import (
    PAGES_PER_CATEGORY,
    extract_amounts_from_card,
    find_cards,
    first_text,
    new_scrape_page,
    page_delay,
)

logger = logging.getLogger(__name__)

CATEGORY_SLUGS: dict[str, str] = {
    "medical": "medical-fundraising",
    "education": "education-fundraising",
    "emergency": "emergency-fundraising",
    "community": "community",
}

_CARD_SELECTORS = [
    "[data-element-context='heroCard']",
    "[class*='story-card']",
    "[class*='fund-card']",
    "[class*='FundCard']",
    "div[class*='grid'] > div > a[href*='/f/']",
]

_TITLE_SELECTORS = [
    "[data-testid='card-title']",
    "[class*='title']",
    "h2",
    "h3",
]

_SNIPPET_SELECTORS = [
    "[data-testid='card-description']",
    "[class*='description']",
    "[class*='story']",
    "p",
]


async def _extract_campaign(card: ElementHandle, category: str) -> Optional[dict]:
    """Extract one GoFundMe campaign from a card element."""
    try:
        link_el = await card.query_selector("a[href*='/f/']")
        if not link_el:
            href = await card.get_attribute("href")
        else:
            href = await link_el.get_attribute("href")

        if not href or "/f/" not in href:
            return None

        campaign_url = href if href.startswith("http") else f"https://www.gofundme.com{href}"
        title = await first_text(card, _TITLE_SELECTORS)
        story_snippet = await first_text(card, _SNIPPET_SELECTORS)

        photo_url: Optional[str] = None
        photo_el = await card.query_selector("img")
        if photo_el:
            photo_url = await photo_el.get_attribute("src") or await photo_el.get_attribute("data-src")

        raised_amount, goal_amount = await extract_amounts_from_card(card)

        location_el = await card.query_selector("[class*='location'], [data-testid*='location']")
        location: Optional[str] = None
        if location_el:
            location = (await location_el.inner_text()).strip() or None

        return {
            "title": title,
            "story_snippet": story_snippet,
            "photo_url": photo_url,
            "goal_amount": goal_amount,
            "raised_amount": raised_amount,
            "platform": "gofundme",
            "campaign_url": campaign_url,
            "category": category,
            "location": location,
        }
    except Exception as exc:
        logger.error("GoFundMe card extraction failed: %s", exc)
        return None


async def scrape_category(browser: Browser, category: str) -> list[dict]:
    """Scrape up to PAGES_PER_CATEGORY pages for one GoFundMe category."""
    slug = CATEGORY_SLUGS.get(category, category)
    campaigns: list[dict] = []
    page = await new_scrape_page(browser)

    try:
        for page_num in range(1, PAGES_PER_CATEGORY + 1):
            url = f"https://www.gofundme.com/discover/{slug}?page={page_num}"
            logger.info("[gofundme/%s] page %d -- %s", category, page_num, url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                found = False
                for sel in _CARD_SELECTORS:
                    try:
                        await page.wait_for_selector(sel, timeout=10_000)
                        found = True
                        break
                    except Exception:
                        continue
                if not found:
                    logger.warning("[gofundme/%s] page %d: no cards, stopping", category, page_num)
                    break
            except Exception as exc:
                logger.error("[gofundme/%s] page %d navigation failed: %s", category, page_num, exc)
                break

            cards = await find_cards(page, _CARD_SELECTORS)
            if not cards:
                logger.info("[gofundme/%s] page %d: empty, stopping", category, page_num)
                break

            logger.info("[gofundme/%s] page %d: %d cards", category, page_num, len(cards))
            for card in cards:
                campaign = await _extract_campaign(card, category)
                if campaign:
                    campaigns.append(campaign)

            await page_delay()
    finally:
        await page.close()

    return campaigns


async def scrape_gofundme(categories: Optional[list[str]] = None) -> list[dict]:
    """Scrape GoFundMe discover pages for all or selected categories."""
    from playwright.async_api import async_playwright

    target = categories or list(CATEGORY_SLUGS.keys())
    all_campaigns: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for cat in target:
                logger.info("=== GoFundMe category: %s ===", cat)
                results = await scrape_category(browser, cat)
                logger.info("=== GoFundMe %s: %d campaigns ===", cat, len(results))
                all_campaigns.extend(results)
        finally:
            await browser.close()

    return all_campaigns
