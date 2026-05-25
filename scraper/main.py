"""Entry point for the GiveFund multi-platform scraper.

Usage:
    python main.py --platform all
    python main.py --platform gofundme
    python main.py --platform gofundme --category medical
"""

import argparse
import asyncio
import logging
import time

from db import count_campaigns, create_table, get_connection, upsert_campaign
from platforms import ALL_PLATFORMS, PLATFORM_SCRAPERS
from platforms.gofundme import CATEGORY_SLUGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def persist_campaigns(conn, campaigns: list[dict]) -> int:
    """Upsert campaigns; log failures and continue."""
    saved = 0
    for campaign in campaigns:
        try:
            await upsert_campaign(conn, campaign)
            saved += 1
        except Exception as exc:
            logger.error(
                "upsert failed for %s: %s",
                campaign.get("campaign_url"),
                exc,
            )
    return saved


async def main(platforms: list[str], category: str | None) -> None:
    """Run scrapers for selected platforms and persist results."""
    async with get_connection() as conn:
        await create_table(conn)

        for platform in platforms:
            start = time.time()
            logger.info("=== Starting %s ===", platform)
            try:
                campaigns = []
                scraper = PLATFORM_SCRAPERS[platform]
                if platform == "gofundme":
                    cats = [category] if category else list(CATEGORY_SLUGS.keys())
                    campaigns = await scraper(cats)
                else:
                    campaigns = await scraper()
                saved = await persist_campaigns(conn, campaigns)
                total = await count_campaigns(conn, platform)
                elapsed = time.time() - start
                logger.info(
                    "=== %s done in %.1fs: scraped=%d saved=%d db_total=%d ===",
                    platform,
                    elapsed,
                    len(campaigns),
                    saved,
                    total,
                )
            except Exception as exc:
                logger.error("=== %s failed: %s ===", platform, exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GiveFund multi-platform scraper")
    parser.add_argument(
        "--platform",
        type=str,
        default="all",
        choices=["all", *ALL_PLATFORMS],
        help="Platform to scrape (default: all)",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=list(CATEGORY_SLUGS.keys()),
        help="GoFundMe only: scrape a single category",
    )
    args = parser.parse_args()

    if args.category and args.platform not in ("gofundme", "all"):
        parser.error("--category is only valid with --platform gofundme or all")

    target_platforms = ALL_PLATFORMS if args.platform == "all" else [args.platform]
    asyncio.run(main(target_platforms, args.category))
