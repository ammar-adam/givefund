"""Islamic Relief Canada Raise for Relief leaderboard (peer fundraisers)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from platforms.base import new_scrape_page

logger = logging.getLogger(__name__)

PLATFORM = "islamicrelief_ca"
LEADERBOARD_URL = "https://fundraise.islamicreliefcanada.org/my/campaign/leaderboard"
BASE = "https://fundraise.islamicreliefcanada.org"

_AMOUNT_RE = re.compile(r"\$[\d,]+\.?\d*")
_CAMPAIGN_PATH_RE = re.compile(
    r'href="(/(?:my/)?campaign/[^"?#]+)"',
    re.I,
)


def _parse_amount(text: str) -> float | None:
    match = _AMOUNT_RE.search(text or "")
    if not match:
        return None
    try:
        return float(match.group().replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _campaign_from_block(title: str, amount: float | None, url: str) -> dict:
    title = re.sub(r"^\d+\s+", "", title.strip())
    title = re.sub(r"\s+\d[\d,]*\s+Supporters.*$", "", title, flags=re.I)
    title = title.strip(" -")
    lower = title.lower()
    category = "community"
    if any(w in lower for w in ("gaza", "palestine", "syria", "yemen", "sudan", "emergency", "flood")):
        category = "emergency"
    elif any(w in lower for w in ("medical", "health", "hospital")):
        category = "medical"
    elif "education" in lower or "school" in lower:
        category = "education"
    return {
        "title": title[:200] if title else "Islamic Relief fundraiser",
        "story_snippet": "Fundraiser on Islamic Relief Canada Raise for Relief.",
        "photo_url": None,
        "goal_amount": None,
        "raised_amount": amount,
        "platform": PLATFORM,
        "campaign_url": url,
        "category": category,
        "location": "Canada",
    }


async def _scrape_via_playwright() -> list[dict]:
    campaigns: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            await page.goto(LEADERBOARD_URL, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(4000)
            for _ in range(4):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
            html = await page.content()
            for match in _CAMPAIGN_PATH_RE.finditer(html):
                path = match.group(1)
                url = urljoin(BASE, path)
                if url in seen or "leaderboard" in url:
                    continue
                seen.add(url)
            links = await page.eval_on_selector_all(
                "a[href*='/campaign/']",
                """els => els.map(a => ({
                    href: a.href,
                    text: (a.innerText || '').trim()
                }))""",
            )
            for item in links:
                url = (item.get("href") or "").split("?")[0]
                text = item.get("text") or ""
                if not url or "leaderboard" in url or url in seen:
                    continue
                seen.add(url)
                amount = _parse_amount(text)
                title = re.sub(r"\$[\d,]+\.?\d*", "", text).strip()
                if len(title) < 5:
                    continue
                campaigns.append(_campaign_from_block(title, amount, url))
                if len(campaigns) >= 80:
                    break

        finally:
            await page.close()
            await browser.close()

    return campaigns


async def scrape_islamicrelief_ca() -> list[dict]:
    """Scrape public leaderboard entries from Islamic Relief Canada."""

    try:
        campaigns = await _scrape_via_playwright()
        logger.info("[%s] total campaigns: %d", PLATFORM, len(campaigns))
        return campaigns
    except Exception as exc:
        logger.error("[%s] scrape failed: %s", PLATFORM, exc)
        return []
