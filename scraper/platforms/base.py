"""Shared scraper utilities for all platforms."""

import logging
import random
import re
from typing import Optional

from playwright.async_api import Browser, ElementHandle, Page

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PAGES_PER_CATEGORY = 5


def parse_amount(text: Optional[str]) -> Optional[float]:
    """Parse currency strings like '$1,234' or '1.2k' into a float."""
    if not text:
        return None
    text = text.strip().lower()
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


async def first_text(element: ElementHandle, selectors: list[str]) -> Optional[str]:
    """Return inner_text from the first matching child selector."""
    for sel in selectors:
        try:
            child = await element.query_selector(sel)
            if child:
                text = (await child.inner_text()).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


async def extract_amounts_from_card(card: ElementHandle) -> tuple[Optional[float], Optional[float]]:
    """Extract raised and goal amounts from card text."""
    raised_amount: Optional[float] = None
    goal_amount: Optional[float] = None
    try:
        all_text = await card.inner_text()
        dollar_values = [
            parse_amount(t) for t in re.findall(r"\$[\d,\.]+[km]?", all_text, re.I)
        ]
        dollar_values = [v for v in dollar_values if v is not None]
        if dollar_values:
            raised_amount = dollar_values[0]
        if len(dollar_values) >= 2:
            goal_amount = dollar_values[1]
    except Exception as exc:
        logger.debug("amount parse failed: %s", exc)
    return raised_amount, goal_amount


async def find_cards(page: Page, selectors: list[str]) -> list[ElementHandle]:
    """Return card elements using the first selector that matches."""
    for sel in selectors:
        try:
            cards = await page.query_selector_all(sel)
            if cards:
                return cards
        except Exception:
            continue
    return []


async def page_delay() -> None:
    """Sleep 2-5 seconds between page loads."""
    import asyncio

    delay = random.uniform(2, 5)
    logger.info("sleeping %.1fs", delay)
    await asyncio.sleep(delay)


async def new_scrape_page(browser: Browser) -> Page:
    """Open a page with the standard GiveFund user agent."""
    page = await browser.new_page()
    await page.set_extra_http_headers({"User-Agent": USER_AGENT})
    return page
