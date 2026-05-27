"""Run live ingestion on an interval (default every 30 minutes)."""

import asyncio
import logging
import os
from datetime import datetime

import schedule

from live_runner import run_live_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _job() -> None:
    """Sync wrapper for one live ingest cycle."""
    logger.info("Scheduled live ingest at %s", datetime.utcnow().isoformat())
    summary = asyncio.run(run_live_cycle())
    logger.info("Scheduled ingest done: %s", summary)


def main() -> None:
    """Schedule live ingest and block forever."""
    minutes = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))
    logger.info("GiveFund live scheduler — every %d minutes", minutes)
    schedule.every(minutes).minutes.do(_job)
    _job()
    while True:
        schedule.run_pending()
        import time

        time.sleep(30)


if __name__ == "__main__":
    main()
