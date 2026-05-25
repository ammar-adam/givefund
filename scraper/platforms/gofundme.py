"""GoFundMe discover scraper — Algolia pagination + Show more DOM expansion."""

import logging
import random
from typing import Any, Optional

from playwright.async_api import Response, async_playwright

from platforms.algolia_client import CATEGORY_ALGOLIA_IDS, AlgoliaSession
from platforms.base import PAGES_PER_CATEGORY, new_scrape_page, page_delay

logger = logging.getLogger(__name__)

CATEGORY_SLUGS: dict[str, str] = {
    "medical": "medical-fundraising",
    "education": "education-fundraising",
    "emergency": "emergency-fundraising",
    "community": "community",
}

LOAD_MORE = 'button:has-text("Show more")'
HITS_PER_PAGE = 50
MAX_ALGOLIA_PAGES = 5


def _money_minor_to_major(amount: Optional[float | int]) -> Optional[float]:
    if amount is None:
        return None
    return round(float(amount) / 100.0, 2)


def _parse_algolia_hit(hit: dict[str, Any], category: str) -> Optional[dict]:
    slug = hit.get("url")
    if not slug or str(slug).startswith("http"):
        return None
    story = (hit.get("funddescription") or "").strip()
    if len(story) > 500:
        story = story[:497] + "..."
    return {
        "title": (hit.get("fundname") or "").strip() or None,
        "story_snippet": story or None,
        "photo_url": hit.get("thumb_img_url"),
        "goal_amount": _money_minor_to_major(hit.get("goalamount")),
        "raised_amount": _money_minor_to_major(hit.get("balance")),
        "platform": "gofundme",
        "campaign_url": f"https://www.gofundme.com/f/{str(slug).split('?')[0]}",
        "category": category,
        "location": hit.get("locationtext"),
    }


def _parse_dom_href(href: str, category: str) -> Optional[dict]:
    if not href or "/f/" not in href or "/create/" in href:
        return None
    slug = href.split("/f/")[-1].split("?")[0]
    if not slug:
        return None
    title = slug.replace("-", " ").title()
    url = href if href.startswith("http") else f"https://www.gofundme.com{href}"
    return {
        "title": title,
        "story_snippet": None,
        "photo_url": None,
        "goal_amount": None,
        "raised_amount": None,
        "platform": "gofundme",
        "campaign_url": url.split("?")[0],
        "category": category,
        "location": None,
    }


async def _click_show_more(page) -> bool:
    btn = await page.query_selector(LOAD_MORE)
    if not btn or not await btn.is_visible():
        return False
    try:
        await btn.scroll_into_view_if_needed()
        await btn.click(timeout=5000)
        await page.wait_for_timeout(random.uniform(2000, 3500))
        return True
    except Exception:
        return False


async def _collect_dom_links(page, category: str) -> list[dict]:
    hrefs = await page.eval_on_selector_all(
        'a[href*="/f/"]',
        """els => [...new Set(els.map(e => e.getAttribute('href')))]
            .filter(h => h && h.includes('/f/') && !h.includes('create'))""",
    )
    campaigns = []
    for href in hrefs:
        c = _parse_dom_href(href, category)
        if c:
            campaigns.append(c)
    return campaigns


async def _scrape_category_algolia(
    session: AlgoliaSession,
    category: str,
    hits_by_url: dict[str, dict],
) -> None:
    """Paginate Algolia for a category when browser credentials are available."""
    cat_id = CATEGORY_ALGOLIA_IDS.get(category)
    if not cat_id or not session.ready():
        return
    for page_num in range(MAX_ALGOLIA_PAGES):
        try:
            hits = await session.fetch_category_page(cat_id, page_num, HITS_PER_PAGE)
        except Exception as exc:
            logger.error("[gofundme/%s] algolia page %d failed: %s", category, page_num, exc)
            break
        if not hits:
            break
        logger.info("[gofundme/%s] algolia page %d: %d hits", category, page_num, len(hits))
        for hit in hits:
            campaign = _parse_algolia_hit(hit, category)
            if campaign:
                hits_by_url[campaign["campaign_url"]] = campaign
        if len(hits) < HITS_PER_PAGE:
            break
        await page_delay()


async def scrape_gofundme(categories: Optional[list[str]] = None) -> list[dict]:
    """Scrape GoFundMe with Algolia pagination and Show-more DOM expansion."""
    target = categories or list(CATEGORY_SLUGS.keys())
    hits_by_url: dict[str, dict] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        session = AlgoliaSession()
        boot_page = await new_scrape_page(browser)
        session.attach(boot_page)

        try:
            await boot_page.goto(
                "https://www.gofundme.com/discover/medical-fundraising",
                wait_until="networkidle",
                timeout=60_000,
            )
            await _click_show_more(boot_page)
            if not session.ready():
                logger.warning("[gofundme] algolia credentials not captured; DOM-only mode")
        finally:
            await boot_page.close()

        for cat in target:
            slug = CATEGORY_SLUGS.get(cat, cat)
            url = f"https://www.gofundme.com/discover/{slug}"
            page = await new_scrape_page(browser)
            hits_store: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            async def capture(response: Response) -> None:
                if "algolia" not in response.url or response.request.method != "POST":
                    return
                try:
                    payload = await response.json()
                except Exception:
                    return
                for result in payload.get("results", []):
                    for hit in result.get("hits", []):
                        oid = hit.get("objectID") or hit.get("url")
                        if oid and oid not in seen_ids:
                            seen_ids.add(oid)
                            hits_store.append(hit)

            page.on("response", capture)
            try:
                logger.info("[gofundme/%s] %s", cat, url)
                await page.goto(url, wait_until="networkidle", timeout=60_000)
                for _ in range(PAGES_PER_CATEGORY):
                    await _click_show_more(page)
                for hit in hits_store:
                    campaign = _parse_algolia_hit(hit, cat)
                    if campaign:
                        hits_by_url[campaign["campaign_url"]] = campaign
                for campaign in await _collect_dom_links(page, cat):
                    hits_by_url.setdefault(campaign["campaign_url"], campaign)
                await _scrape_category_algolia(session, cat, hits_by_url)
                await page_delay()
            except Exception as exc:
                logger.error("[gofundme/%s] failed: %s", cat, exc)
            finally:
                await page.close()

        await browser.close()

    campaigns = list(hits_by_url.values())
    logger.info("[gofundme] total unique campaigns: %d", len(campaigns))
    return campaigns
