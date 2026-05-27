"""
Live ingestion — scrape all platforms, refresh DB continuously.

GoFundMe runs first (Algolia scale). Other platforms run in parallel.
Use: python live_runner.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Callable, Awaitable

from db import (
    count_campaigns,
    create_table,
    finish_ingest_run,
    get_connection,
    persist_campaigns_batch,
    record_platform_stat,
    start_ingest_run,
)
from platforms import ALL_PLATFORMS, PLATFORM_SCRAPERS
from platforms.gofundme import CATEGORY_SLUGS

logger = logging.getLogger(__name__)

HEAVY_PLATFORMS = frozenset({"gofundme"})
DEFAULT_PARALLEL = int(os.getenv("SCRAPE_PARALLEL", "4"))


async def _run_one_platform(
    conn,
    run_id: int,
    platform: str,
    sem: asyncio.Semaphore,
) -> tuple[str, int, int, int, float, str | None]:
    async with sem:
        start = time.perf_counter()
        scraped = 0
        saved = 0
        err: str | None = None
        try:
            scraper = PLATFORM_SCRAPERS[platform]
            if platform == "gofundme":
                campaigns = await scraper(list(CATEGORY_SLUGS.keys()))
            else:
                campaigns = await scraper()
            scraped = len(campaigns)
            saved = await persist_campaigns_batch(conn, campaigns)
        except Exception as exc:
            err = str(exc)[:500]
            logger.exception("[%s] live scrape failed", platform)
        duration = time.perf_counter() - start
        total = await count_campaigns(conn, platform)
        await record_platform_stat(
            conn, run_id, platform, scraped, saved, total, duration, err
        )
        logger.info(
            "[%s] live done %.1fs scraped=%d saved=%d db_total=%d",
            platform,
            duration,
            scraped,
            saved,
            total,
        )
        return platform, scraped, saved, total, duration, err


async def run_live_cycle(
    platforms: list[str] | None = None,
    *,
    parallel: int = DEFAULT_PARALLEL,
) -> dict:
    """
    One full live ingest cycle across all (or selected) platforms.
    Returns summary dict for API / logging.
    """

    targets = platforms or list(ALL_PLATFORMS)
    sem = asyncio.Semaphore(max(1, parallel))
    total_scraped = 0
    total_saved = 0
    errors: list[str] = []

    async with get_connection() as conn:
        await create_table(conn)
        run_id = await start_ingest_run(conn)

        try:
            # Phase 1: GoFundMe alone (memory + browser heavy)
            if "gofundme" in targets:
                _, s, sv, _, _, err = await _run_one_platform(
                    conn, run_id, "gofundme", asyncio.Semaphore(1)
                )
                total_scraped += s
                total_saved += sv
                if err:
                    errors.append(f"gofundme: {err}")

            # Phase 2: everything else in parallel
            rest = [p for p in targets if p != "gofundme"]
            if rest:
                results = await asyncio.gather(
                    *[
                        _run_one_platform(conn, run_id, p, sem)
                        for p in rest
                    ],
                    return_exceptions=True,
                )
                for item in results:
                    if isinstance(item, Exception):
                        errors.append(str(item))
                        continue
                    _, s, sv, _, _, err = item
                    total_scraped += s
                    total_saved += sv
                    if err:
                        errors.append(f"{item[0]}: {err}")

            total_all = await count_campaigns(conn)
            notes = "; ".join(errors[:8]) if errors else None
            status = "partial" if errors else "ok"
            await finish_ingest_run(
                conn,
                run_id,
                total_scraped=total_scraped,
                total_saved=total_saved,
                status=status,
                notes=notes,
            )
            return {
                "run_id": run_id,
                "status": status,
                "total_scraped": total_scraped,
                "total_saved": total_saved,
                "total_campaigns": total_all,
                "errors": errors,
            }
        except Exception as exc:
            await finish_ingest_run(
                conn,
                run_id,
                total_scraped=total_scraped,
                total_saved=total_saved,
                status="failed",
                notes=str(exc),
            )
            raise


async def run_live_loop(interval_sec: int) -> None:
    """Run live cycles forever."""

    cycle = 0
    while True:
        cycle += 1
        logger.info("========== live cycle %d ==========", cycle)
        started = time.perf_counter()
        try:
            summary = await run_live_cycle()
            logger.info(
                "Live cycle %d complete in %.0fs — %d campaigns in DB (%d saved this run)",
                cycle,
                time.perf_counter() - started,
                summary["total_campaigns"],
                summary["total_saved"],
            )
        except Exception as exc:
            logger.error("Live cycle %d failed: %s", cycle, exc)
        logger.info("Sleeping %ds until next live cycle", interval_sec)
        await asyncio.sleep(interval_sec)


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="GiveFund live ingestion")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("SCRAPE_INTERVAL", "1800")),
        help="Seconds between cycles (default 1800 = 30 min)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single cycle then exit",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        help="Max parallel platform scrapers (excluding GoFundMe)",
    )
    args = parser.parse_args()

    if args.once:
        summary = asyncio.run(
            run_live_cycle(parallel=args.parallel)
        )
        logger.info("Done: %s", summary)
    else:
        asyncio.run(run_live_loop(args.interval))


if __name__ == "__main__":
    main()
