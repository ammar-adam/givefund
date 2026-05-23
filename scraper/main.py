"""Entry point for the GiveFund scraper.

Usage:
    python main.py                        # scrape all categories
    python main.py --category medical     # scrape one category
"""

import argparse
import asyncio
import logging

from db import create_table, get_connection, upsert_campaign
from scraper import CATEGORY_SLUGS, run_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main(categories: list[str]) -> None:
    """Scrape the given categories and persist every campaign to givefund.db."""
    async with get_connection() as conn:
        await create_table(conn)
        campaigns = await run_scraper(categories)

        inserted = 0
        for campaign in campaigns:
            try:
                await upsert_campaign(conn, campaign)
                inserted += 1
            except Exception as exc:
                logger.error("upsert failed for %s: %s", campaign.get("campaign_url"), exc)

        logger.info("Done -- %d / %d campaigns saved to DB.", inserted, len(campaigns))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GiveFund scraper")
    parser.add_argument(
        "--category",
        type=str,
        choices=list(CATEGORY_SLUGS.keys()),
        help="Scrape a single category instead of all four",
    )
    args = parser.parse_args()

    target_categories: list[str] = (
        [args.category] if args.category else list(CATEGORY_SLUGS.keys())
    )
    asyncio.run(main(target_categories))
