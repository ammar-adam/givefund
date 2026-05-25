"""Run all platform scrapers every 24 hours."""

import asyncio
import logging
import time
from datetime import datetime

import schedule

from db import count_campaigns, create_table, get_connection
from main import persist_campaigns
from platforms import ALL_PLATFORMS, PLATFORM_SCRAPERS
from platforms.gofundme import CATEGORY_SLUGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def run_all_platforms() -> None:
    """Scrape every platform once and log timing plus row counts."""
    run_start = datetime.utcnow().isoformat()
    logger.info("Scheduled run started at %s", run_start)

    async with get_connection() as conn:
        await create_table(conn)

        for platform in ALL_PLATFORMS:
            start = time.time()
            logger.info("[%s] scrape start", platform)
            try:
                scraper = PLATFORM_SCRAPERS[platform]
                if platform == "gofundme":
                    campaigns = await scraper(list(CATEGORY_SLUGS.keys()))
                else:
                    campaigns = await scraper()
                saved = await persist_campaigns(conn, campaigns)
                total = await count_campaigns(conn, platform)
                elapsed = time.time() - start
                logger.info(
                    "[%s] end=%s duration=%.1fs scraped=%d saved=%d db_rows=%d",
                    platform,
                    datetime.utcnow().isoformat(),
                    elapsed,
                    len(campaigns),
                    saved,
                    total,
                )
            except Exception as exc:
                logger.error("[%s] run failed: %s", platform, exc)

    logger.info("Scheduled run finished at %s", datetime.utcnow().isoformat())


def _job() -> None:
    """Sync wrapper for the async scrape job."""
    asyncio.run(run_all_platforms())


def main() -> None:
    """Schedule daily scrapes and block forever."""
    logger.info("GiveFund scheduler started (every 24 hours)")
    schedule.every(24).hours.do(_job)
    _job()
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
