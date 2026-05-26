"""LaunchGood discover scraper — list from /discover, enrich each campaign page."""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright

from platforms.base import PAGES_PER_CATEGORY, new_scrape_page, page_delay, parse_amount

logger = logging.getLogger(__name__)

DISCOVER_URLS = (
    "https://www.launchgood.com/discover",
    "https://www.launchgood.com/explore",
)
MAX_ENRICH = 50  # cap per run to stay polite and fast


def _category_from_text(text: str) -> str:
    """Infer category from title/description keywords."""
    lower = text.lower()
    for key in ("medical", "education", "emergency"):
        if key in lower:
            return key
    return "community"


async def _discover_links(page: Page) -> list[str]:
    """Collect unique campaign URLs from the discover page."""
    for _ in range(PAGES_PER_CATEGORY):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

    hrefs = await page.eval_on_selector_all(
        'a[href*="/v4/campaign/"]',
        """els => [...new Set(els.map(e => e.href.split('?')[0]))]""",
    )
    return [h for h in hrefs if "/v4/campaign/" in h][: MAX_ENRICH * 2]


async def _enrich_campaign(page: Page, campaign_url: str) -> Optional[dict]:
    """Visit a campaign page and extract metadata from OG tags and visible amounts."""
    try:
        await page.goto(campaign_url, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(1500)

        meta = await page.evaluate("""() => {
          const og = (k) => document.querySelector(`meta[property="og:${k}"]`)?.content;
          const title = og('title') || document.querySelector('h1')?.innerText;
          const desc = og('description') || '';
          const image = og('image');
          return { title, desc, image };
        }""")

        body_sample = (await page.inner_text("body"))[:8000]
        amounts = [
            parse_amount(m)
            for m in re.findall(r"\$[\d,\.]+", body_sample)
        ]
        amounts = [a for a in amounts if a is not None and a > 0]
        raised = amounts[0] if amounts else None
        goal = amounts[1] if len(amounts) > 1 else None

        title = (meta.get("title") or "").strip()
        if not title:
            slug = urlparse(campaign_url).path.split("/")[-1]
            title = slug.replace("_", " ").title()

        story = (meta.get("desc") or "").strip()
        if len(story) > 500:
            story = story[:497] + "..."

        text_blob = f"{title} {story}"
        return {
            "title": title,
            "story_snippet": story or None,
            "photo_url": meta.get("image"),
            "goal_amount": goal,
            "raised_amount": raised,
            "platform": "launchgood",
            "campaign_url": campaign_url,
            "category": _category_from_text(text_blob),
            "location": None,
        }
    except Exception as exc:
        logger.error("[launchgood] enrich failed %s: %s", campaign_url, exc)
        return None


async def scrape_launchgood() -> list[dict]:
    """Scrape LaunchGood discover and enrich campaign pages."""
    campaigns: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        list_page = await new_scrape_page(browser)
        try:
            urls: list[str] = []
            for discover_url in DISCOVER_URLS:
                logger.info("[launchgood] %s", discover_url)
                try:
                    await list_page.goto(
                        discover_url, wait_until="commit", timeout=120_000
                    )
                    await list_page.wait_for_timeout(3000)
                    found = await _discover_links(list_page)
                    urls.extend(found)
                    logger.info("[launchgood] %s → %d urls", discover_url, len(found))
                except Exception as exc:
                    logger.error("[launchgood] discover failed %s: %s", discover_url, exc)
            urls = list(dict.fromkeys(urls))
            logger.info("[launchgood] found %d campaign urls", len(urls))
        finally:
            await list_page.close()

        enrich_page = await new_scrape_page(browser)
        try:
            for i, url in enumerate(urls[:MAX_ENRICH]):
                if url in seen:
                    continue
                seen.add(url)
                campaign = await _enrich_campaign(enrich_page, url)
                if campaign:
                    campaigns.append(campaign)
                if (i + 1) % 5 == 0:
                    logger.info("[launchgood] enriched %d/%d", i + 1, min(len(urls), MAX_ENRICH))
                await asyncio.sleep(2)
        finally:
            await enrich_page.close()
            await browser.close()

    logger.info("[launchgood] total campaigns: %d", len(campaigns))
    return campaigns
