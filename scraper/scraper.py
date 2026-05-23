"""GoFundMe scraper using Playwright async API."""

import asyncio
import logging
import random
import re
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, ElementHandle

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CATEGORY_SLUGS: dict[str, str] = {
    "medical": "medical-fundraising",
    "education": "education-fundraising",
    "emergency": "emergency-fundraising",
    "community": "community",
}

PAGES_PER_CATEGORY = 10

# Selectors ordered from most-specific to broadest fallback
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

_AMOUNT_SELECTORS = [
    "[data-testid='card-progress-label']",
    "[class*='progress-meter']",
    "[class*='amount']",
    "[class*='raised']",
]


def _parse_amount(text: Optional[str]) -> Optional[float]:
    """Parse a currency string like '$1,234.56' or '1.2k' into a float."""
    if not text:
        return None
    text = text.strip().lower()
    # handle shorthand like '$1.2k' or '1.5m'
    multiplier = 1.0
    if text.endswith("k"):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


async def _first_text(element: ElementHandle, selectors: list[str]) -> Optional[str]:
    """Try each selector on element, return inner_text of the first match."""
    for sel in selectors:
        try:
            child = await element.query_selector(sel)
            if child:
                return (await child.inner_text()).strip() or None
        except Exception:
            continue
    return None


async def _extract_campaign(card: ElementHandle, category: str) -> Optional[dict]:
    """Extract a campaign dict from a single card element. Returns None on hard failure."""
    try:
        # campaign URL -- required
        link_el = await card.query_selector("a[href*='/f/']")
        if not link_el:
            # card might itself be an <a>
            tag = await card.get_attribute("href")
            href = tag if tag and "/f/" in tag else None
        else:
            href = await link_el.get_attribute("href")

        if not href:
            return None
        campaign_url = href if href.startswith("http") else f"https://www.gofundme.com{href}"

        title = await _first_text(card, _TITLE_SELECTORS)
        story_snippet = await _first_text(card, _SNIPPET_SELECTORS)

        photo_el = await card.query_selector("img")
        photo_url: Optional[str] = None
        if photo_el:
            photo_url = (
                await photo_el.get_attribute("src")
                or await photo_el.get_attribute("data-src")
            )

        # Amounts: look for text blocks that contain currency values
        raised_amount: Optional[float] = None
        goal_amount: Optional[float] = None

        amount_els = await card.query_selector_all(", ".join(_AMOUNT_SELECTORS))
        for el in amount_els:
            try:
                text = (await el.inner_text()).lower()
                # Extract all numeric values from the text
                amounts = [_parse_amount(t) for t in re.findall(r"\$[\d,\.]+[km]?", text)]
                amounts = [a for a in amounts if a is not None]
                if "raised" in text and amounts:
                    raised_amount = amounts[0]
                if ("goal" in text or "of $" in text) and len(amounts) >= 2:
                    goal_amount = amounts[1]
                elif ("goal" in text or "of $" in text) and amounts:
                    goal_amount = amounts[0]
            except Exception:
                continue

        # Fallback: grab any two dollar amounts from the whole card text
        if raised_amount is None or goal_amount is None:
            try:
                all_text = await card.inner_text()
                dollar_values = [_parse_amount(t) for t in re.findall(r"\$[\d,\.]+[km]?", all_text)]
                dollar_values = [v for v in dollar_values if v is not None]
                if raised_amount is None and dollar_values:
                    raised_amount = dollar_values[0]
                if goal_amount is None and len(dollar_values) >= 2:
                    goal_amount = dollar_values[1]
            except Exception:
                pass

        return {
            "title": title,
            "story_snippet": story_snippet,
            "photo_url": photo_url,
            "goal_amount": goal_amount,
            "raised_amount": raised_amount,
            "platform": "gofundme",
            "campaign_url": campaign_url,
            "category": category,
        }
    except Exception as exc:
        logger.error("Card extraction failed: %s", exc)
        return None


async def _find_cards(page: Page) -> list[ElementHandle]:
    """Return campaign card elements using the first selector that produces results."""
    for sel in _CARD_SELECTORS:
        try:
            cards = await page.query_selector_all(sel)
            if cards:
                return cards
        except Exception:
            continue
    return []


async def scrape_category(browser: Browser, category: str) -> list[dict]:
    """Scrape up to PAGES_PER_CATEGORY pages for one category; return campaign dicts."""
    slug = CATEGORY_SLUGS.get(category, category)
    campaigns: list[dict] = []
    page = await browser.new_page()
    await page.set_extra_http_headers({"User-Agent": USER_AGENT})

    try:
        for page_num in range(1, PAGES_PER_CATEGORY + 1):
            url = f"https://www.gofundme.com/discover/{slug}?page={page_num}"
            logger.info("[%s] page %d -- %s", category, page_num, url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                # Wait up to 10s for any known card selector to appear
                found = False
                for sel in _CARD_SELECTORS:
                    try:
                        await page.wait_for_selector(sel, timeout=10_000)
                        found = True
                        break
                    except Exception:
                        continue
                if not found:
                    logger.warning("[%s] page %d: no cards after all selectors, stopping", category, page_num)
                    break
            except Exception as exc:
                logger.error("[%s] page %d: navigation failed -- %s", category, page_num, exc)
                break

            cards = await _find_cards(page)
            if not cards:
                logger.info("[%s] page %d: empty page, stopping", category, page_num)
                break

            logger.info("[%s] page %d: found %d cards", category, page_num, len(cards))
            for card in cards:
                campaign = await _extract_campaign(card, category)
                if campaign:
                    campaigns.append(campaign)

            delay = random.uniform(2, 4)
            logger.info("[%s] sleeping %.1fs", category, delay)
            await asyncio.sleep(delay)
    finally:
        await page.close()

    return campaigns


async def run_scraper(categories: list[str]) -> list[dict]:
    """Launch a headless Chromium browser and scrape all specified categories."""
    all_campaigns: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for cat in categories:
                logger.info("=== Scraping category: %s ===", cat)
                campaigns = await scrape_category(browser, cat)
                logger.info("=== %s: %d campaigns ===", cat, len(campaigns))
                all_campaigns.extend(campaigns)
        finally:
            await browser.close()
    return all_campaigns
