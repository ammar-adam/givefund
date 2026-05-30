"""Generic discover-page scraper for additional crowdfunding platforms."""

import logging
import os
import re
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import quote_plus, urljoin, urlparse

from playwright.async_api import ElementHandle, async_playwright

from platforms.base import (
    PAGES_PER_CATEGORY,
    extract_amounts_from_card,
    find_cards,
    first_text,
    new_scrape_page,
    page_delay,
)

logger = logging.getLogger(__name__)

_TITLE_SELECTORS = ["h1", "h2", "h3", "[class*='title']"]
_SNIPPET_SELECTORS = ["p", "[class*='description']", "[class*='story']"]


@dataclass(frozen=True)
class DiscoverConfig:
    """Configuration for a platform's public listing pages."""

    platform: str
    base_url: str
    start_urls: tuple[str, ...]
    link_markers: tuple[str, ...]
    card_selectors: tuple[str, ...] = ("article", "a[href]", "[class*='card']")
    max_pages: int = 5
    max_campaigns: int = int(os.getenv("DISCOVER_MAX_CAMPAIGNS", "200"))
    search_url_template: str | None = None


def _category_from_text(text: str) -> str:
    lower = text.lower()
    for key in ("medical", "education", "emergency"):
        if key in lower:
            return key
    return "community"


def _campaign_from_url(url: str, platform: str) -> dict:
    """Build a minimal campaign row from a listing URL (no extra page load)."""
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    title = slug.replace("-", " ").replace("_", " ").title() if slug else "Campaign"
    return {
        "title": title,
        "story_snippet": None,
        "photo_url": None,
        "goal_amount": None,
        "raised_amount": None,
        "platform": platform,
        "campaign_url": url,
        "category": _category_from_text(title),
        "location": None,
    }


def _normalize_url(href: str, base_url: str) -> Optional[str]:
    if not href or not any(m in href for m in ("http", "/")):
        return None
    full = href if href.startswith("http") else urljoin(base_url, href)
    return full.split("?")[0].split("#")[0]


def extract_hrefs_from_html(html: str, config: DiscoverConfig) -> set[str]:
    """Parse campaign links from raw HTML (no JavaScript)."""
    hrefs: set[str] = set()
    for marker in config.link_markers:
        pattern = rf'href="([^"]*{re.escape(marker)}[^"]*)"'
        for match in re.findall(pattern, html, re.I):
            norm = _normalize_url(match, config.base_url)
            if norm:
                hrefs.add(norm)
        pattern2 = rf"href='([^']*{re.escape(marker)}[^']*)'"
        for match in re.findall(pattern2, html, re.I):
            norm = _normalize_url(match, config.base_url)
            if norm:
                hrefs.add(norm)
    # Broad href sweep (catches JSON-escaped and alternate attribute order)
    for raw in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
        norm = _normalize_url(raw, config.base_url)
        if norm and any(m in norm for m in config.link_markers):
            hrefs.add(norm)
    # Next.js __NEXT_DATA__ often lists project URLs
    for block in re.findall(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>',
        html,
        re.I | re.S,
    ):
        for marker in config.link_markers:
            core = marker.strip("/")
            if not core:
                continue
            for path in re.findall(
                rf'"(/?[^"]*{re.escape(core)}[^"]*)"',
                block,
            ):
                norm = _normalize_url(path, config.base_url)
                if norm:
                    hrefs.add(norm)
    return hrefs


async def scrape_search_http(
    config: DiscoverConfig,
    query: str,
    *,
    client=None,
    limit: int | None = None,
) -> list[dict]:
    """
    Fast search via HTTP GET + HTML link harvest (~1–4s per platform).
    Works on many sites without Playwright; JS-heavy sites may return [].
    """
    if not config.search_url_template or not query.strip():
        return []

    import httpx

    search_url = config.search_url_template.format(query=quote_plus(query.strip()))
    cap = limit or min(config.max_campaigns, 20)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(8.0, connect=5.0),
            headers=headers,
        )

    campaigns: list[dict] = []
    try:
        resp = await client.get(search_url)
        if resp.status_code >= 400:
            logger.warning("[%s] HTTP %s for %r", config.platform, resp.status_code, query)
            return []
        hrefs = extract_hrefs_from_html(resp.text, config)
        for url in list(hrefs)[:cap]:
            campaigns.append(_campaign_from_url(url, config.platform))
        logger.info("[%s] HTTP search %r -> %d", config.platform, query, len(campaigns))
    except Exception as exc:
        logger.debug("[%s] HTTP search failed %r: %s", config.platform, query, exc)
    finally:
        if own_client:
            await client.aclose()

    return campaigns


async def _extract_from_link(
    page,
    url: str,
    platform: str,
    card: Optional[ElementHandle],
) -> Optional[dict]:
    """Build campaign dict from a listing card or by visiting the URL."""
    title: Optional[str] = None
    story: Optional[str] = None
    photo: Optional[str] = None
    raised: Optional[float] = None
    goal: Optional[float] = None

    if card:
        title = await first_text(card, _TITLE_SELECTORS)
        story = await first_text(card, _SNIPPET_SELECTORS)
        img = await card.query_selector("img")
        if img:
            photo = await img.get_attribute("src") or await img.get_attribute("data-src")
        raised, goal = await extract_amounts_from_card(card)

    if not title:
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").replace("_", " ").title() if slug else "Campaign"

    if len((story or "")) > 500:
        story = story[:497] + "..."

    return {
        "title": title,
        "story_snippet": story,
        "photo_url": photo,
        "goal_amount": goal,
        "raised_amount": raised,
        "platform": platform,
        "campaign_url": url,
        "category": _category_from_text(f"{title} {story}"),
        "location": None,
    }


async def scrape_discover(config: DiscoverConfig) -> list[dict]:
    """Scrape campaign links from configured discover/listing URLs."""
    campaigns: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            for start_url in config.start_urls[: config.max_pages]:
                logger.info("[%s] %s", config.platform, start_url)
                try:
                    await page.goto(start_url, wait_until="domcontentloaded", timeout=45_000)
                    await page.wait_for_timeout(2500)
                except Exception as exc:
                    logger.error("[%s] navigation failed %s: %s", config.platform, start_url, exc)
                    continue

                hrefs: set[str] = set()
                try:
                    anchor_hrefs = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.href)",
                    )
                    for raw in anchor_hrefs:
                        norm = _normalize_url(raw, config.base_url)
                        if norm and any(m in norm for m in config.link_markers):
                            hrefs.add(norm)
                except Exception:
                    pass

                html = await page.content()
                for marker in config.link_markers:
                    pattern = rf'href="([^"]*{re.escape(marker)}[^"]*)"'
                    for match in re.findall(pattern, html, re.I):
                        norm = _normalize_url(match, config.base_url)
                        if norm:
                            hrefs.add(norm)

                cards = await find_cards(page, list(config.card_selectors))
                for card in cards:
                    try:
                        href = await card.get_attribute("href")
                        if not href:
                            link = await card.query_selector("a")
                            href = await link.get_attribute("href") if link else None
                        norm = _normalize_url(href or "", config.base_url)
                        if norm and any(m in norm for m in config.link_markers):
                            hrefs.add(norm)
                    except Exception:
                        continue

                logger.info("[%s] found %d urls on %s", config.platform, len(hrefs), start_url)
                for url in list(hrefs)[: config.max_campaigns]:
                    if url in seen:
                        continue
                    seen.add(url)
                    try:
                        campaign = await _extract_from_link(page, url, config.platform, None)
                        if campaign:
                            campaigns.append(campaign)
                    except Exception as exc:
                        logger.error("[%s] extract failed %s: %s", config.platform, url, exc)

                await page_delay()
        finally:
            await page.close()
            await browser.close()

    logger.info("[%s] total campaigns: %d", config.platform, len(campaigns))
    return campaigns


async def scrape_search_on_page(
    page,
    config: DiscoverConfig,
    query: str,
    *,
    enrich: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Harvest campaign links from an already-open search results page."""
    if not config.search_url_template or not query.strip():
        return []

    search_url = config.search_url_template.format(query=quote_plus(query.strip()))
    campaigns: list[dict] = []
    seen: set[str] = set()
    cap = limit or min(config.max_campaigns, 25)

    logger.info("[%s] search %r -> %s", config.platform, query, search_url)
    await page.goto(search_url, wait_until="domcontentloaded", timeout=25_000)
    await page.wait_for_timeout(1500)

    hrefs: set[str] = set()
    try:
        for raw in await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)"):
            norm = _normalize_url(raw, config.base_url)
            if norm and any(m in norm for m in config.link_markers):
                hrefs.add(norm)
    except Exception:
        pass

    html = await page.content()
    for marker in config.link_markers:
        pattern = rf'href="([^"]*{re.escape(marker)}[^"]*)"'
        for match in re.findall(pattern, html, re.I):
            norm = _normalize_url(match, config.base_url)
            if norm:
                hrefs.add(norm)

    for url in list(hrefs)[:cap]:
        if url in seen:
            continue
        seen.add(url)
        if enrich:
            campaign = await _extract_from_link(page, url, config.platform, None)
        else:
            campaign = _campaign_from_url(url, config.platform)
        if campaign:
            campaigns.append(campaign)

    logger.info("[%s] search %r -> %d campaigns", config.platform, query, len(campaigns))
    return campaigns


async def scrape_search(
    config: DiscoverConfig,
    query: str,
    *,
    browser=None,
    enrich: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Live search: open platform search URL and harvest campaign links."""
    if browser is not None:
        page = await new_scrape_page(browser)
        try:
            return await scrape_search_on_page(
                page, config, query, enrich=enrich, limit=limit
            )
        except Exception as exc:
            logger.error("[%s] search failed %r: %s", config.platform, query, exc)
            return []
        finally:
            await page.close()

    campaigns: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await new_scrape_page(browser)
        try:
            campaigns = await scrape_search_on_page(
                page, config, query, enrich=enrich, limit=limit
            )
        except Exception as exc:
            logger.error("[%s] search failed %r: %s", config.platform, query, exc)
        finally:
            await page.close()
            await browser.close()

    return campaigns


def make_scraper(config: DiscoverConfig) -> Callable[[], list]:
    """Return an async scraper function for main.py registry."""

    async def _run() -> list[dict]:
        return await scrape_discover(config)

    return _run
