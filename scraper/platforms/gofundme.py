"""GoFundMe discover scraper via in-page Algolia responses (no public API key)."""

import logging
from typing import Any, Optional

from playwright.async_api import Response, async_playwright

from platforms.base import PAGES_PER_CATEGORY, new_scrape_page, page_delay

logger = logging.getLogger(__name__)

CATEGORY_SLUGS: dict[str, str] = {
    "medical": "medical-fundraising",
    "education": "education-fundraising",
    "emergency": "emergency-fundraising",
    "community": "community",
}


def _money_minor_to_major(amount: Optional[float | int]) -> Optional[float]:
    """Convert GoFundMe Algolia minor units (cents) to dollars."""
    if amount is None:
        return None
    return round(float(amount) / 100.0, 2)


def _parse_algolia_hit(hit: dict[str, Any], category: str) -> Optional[dict]:
    """Map one Algolia hit to our campaign schema."""
    slug = hit.get("url")
    if not slug or slug.startswith("http"):
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
        "campaign_url": f"https://www.gofundme.com/f/{slug.split('?')[0]}",
        "category": category,
        "location": hit.get("locationtext"),
    }


async def scrape_gofundme(categories: Optional[list[str]] = None) -> list[dict]:
    """Scrape GoFundMe discover categories using Algolia responses in Playwright."""
    target = categories or list(CATEGORY_SLUGS.keys())
    all_campaigns: list[dict] = []
    seen_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
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
                    for scroll_num in range(PAGES_PER_CATEGORY):
                        await page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                        await page.wait_for_timeout(2500)
                    logger.info("[gofundme/%s] algolia hits: %d", cat, len(hits_store))
                    for hit in hits_store:
                        try:
                            campaign = _parse_algolia_hit(hit, cat)
                            if campaign and campaign["campaign_url"] not in seen_urls:
                                seen_urls.add(campaign["campaign_url"])
                                all_campaigns.append(campaign)
                        except Exception as exc:
                            logger.error("[gofundme] hit parse failed: %s", exc)
                    await page_delay()
                except Exception as exc:
                    logger.error("[gofundme/%s] scrape failed: %s", cat, exc)
                finally:
                    await page.close()
        finally:
            await browser.close()

    logger.info("[gofundme] total campaigns: %d", len(all_campaigns))
    return all_campaigns
