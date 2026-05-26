"""Islamic Relief Canada Raise for Relief leaderboard (peer fundraisers)."""

from __future__ import annotations

import logging
import re
from typing import Any
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
_LEADERBOARD_LINE_RE = re.compile(
    r"(?:Fundraising With Islamic Relief|Supporting Our Masjids)\s+(.+?)\s+(\$[\d,]+\.?\d*)",
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


def _walk_for_campaigns(obj: Any, found: list[dict], seen: set[str]) -> None:
    """Recursively find campaign-like dicts in JSON API responses."""

    if isinstance(obj, dict):
        url = obj.get("url") or obj.get("permalink") or obj.get("link")
        if isinstance(url, str) and "/campaign" in url:
            full = url if url.startswith("http") else urljoin(BASE, url)
            full = full.split("?")[0]
            if full not in seen and "leaderboard" not in full:
                seen.add(full)
                title = (
                    obj.get("name")
                    or obj.get("title")
                    or obj.get("headline")
                    or ""
                )
                amount = obj.get("totalRaised") or obj.get("raised") or obj.get("amount")
                if isinstance(amount, dict):
                    amount = amount.get("amount") or amount.get("value")
                raised = float(amount) / 100 if isinstance(amount, int) and amount > 10000 else amount
                if isinstance(raised, (int, float)):
                    pass
                elif isinstance(raised, str):
                    raised = _parse_amount(raised)
                else:
                    raised = None
                found.append(_campaign_from_block(str(title), raised, full))
        for v in obj.values():
            _walk_for_campaigns(v, found, seen)
    elif isinstance(obj, list):
        for item in obj:
            _walk_for_campaigns(item, found, seen)


async def _scrape_via_playwright() -> list[dict]:
    campaigns: list[dict] = []
    seen: set[str] = set()
    api_hits: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)

        async def on_response(response) -> None:
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct or response.status != 200:
                    return
                if "campaign" not in response.url.lower() and "raisely" not in response.url:
                    return
                body = await response.json()
                before = len(api_hits)
                _walk_for_campaigns(body, api_hits, seen)
                if len(api_hits) > before:
                    logger.info("[%s] API %s +%d", PLATFORM, response.url[:80], len(api_hits) - before)
            except Exception:
                pass

        page.on("response", on_response)
        try:
            await page.goto(LEADERBOARD_URL, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(6000)
            for _ in range(8):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1200)

            campaigns.extend(api_hits)
            seen.update(c["campaign_url"] for c in campaigns)

            html = await page.content()
            for match in _CAMPAIGN_PATH_RE.finditer(html):
                url = urljoin(BASE, match.group(1)).split("?")[0]
                if url not in seen and "leaderboard" not in url:
                    seen.add(url)
                    campaigns.append(_campaign_from_block("", None, url))

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
                if len(title) < 3:
                    continue
                campaigns.append(_campaign_from_block(title, amount, url))

            if len(campaigns) < 15:
                body = await page.inner_text("body")
                for match in _LEADERBOARD_LINE_RE.finditer(body):
                    title = match.group(1).strip()
                    amount = _parse_amount(match.group(2))
                    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:60].strip("-")
                    url = f"{BASE}/my/campaign/{slug}"
                    if url in seen:
                        continue
                    seen.add(url)
                    campaigns.append(_campaign_from_block(title, amount, url))
                    if len(campaigns) >= 40:
                        break

        finally:
            await page.close()
            await browser.close()

    return campaigns[:80]


async def scrape_islamicrelief_ca() -> list[dict]:
    """Scrape public leaderboard entries from Islamic Relief Canada."""

    try:
        campaigns = await _scrape_via_playwright()
        logger.info("[%s] total campaigns: %d", PLATFORM, len(campaigns))
        return campaigns
    except Exception as exc:
        logger.error("[%s] scrape failed: %s", PLATFORM, exc)
        return []
