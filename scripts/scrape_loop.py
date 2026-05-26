#!/usr/bin/env python3
"""
Continuous scrape loop for GiveFund.

Runs all registered platforms in rotation, then sleeps and repeats.
Use for local/dev background ingestion:

    python scripts/scrape_loop.py
    python scripts/scrape_loop.py --interval 3600 --platforms launchgood,islamicrelief_ca,ketto

Environment:
    DB_PATH          — SQLite path (default: ./givefund.db)
    SCRAPE_INTERVAL  — seconds between full cycles (default: 7200 = 2h)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRAPER_DIR = ROOT / "scraper"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("scrape_loop")


def run_platform(platform: str) -> bool:
    """Run one platform scraper subprocess; return success."""

    env = os.environ.copy()
    env.setdefault("DB_PATH", str(ROOT / "givefund.db"))
    cmd = [sys.executable, "main.py", "--platform", platform]
    logger.info("=== starting %s ===", platform)
    try:
        result = subprocess.run(
            cmd,
            cwd=SCRAPER_DIR,
            env=env,
            timeout=int(os.getenv("SCRAPE_PLATFORM_TIMEOUT", "1800")),
            check=False,
        )
        ok = result.returncode == 0
        logger.info("=== %s finished (exit %d) ===", platform, result.returncode)
        return ok
    except subprocess.TimeoutExpired:
        logger.error("=== %s timed out ===", platform)
        return False
    except Exception as exc:
        logger.error("=== %s error: %s ===", platform, exc)
        return False


def list_platforms() -> list[str]:
    sys.path.insert(0, str(SCRAPER_DIR))
    from platforms import ALL_PLATFORMS  # noqa: WPS433

    return list(ALL_PLATFORMS)


def main() -> None:
    parser = argparse.ArgumentParser(description="GiveFund continuous scrape loop")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("SCRAPE_INTERVAL", "7200")),
        help="Seconds between full rotation cycles (default: 7200)",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default=os.getenv("SCRAPE_PLATFORMS", ""),
        help="Comma-separated platform ids (default: all)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one full cycle then exit",
    )
    args = parser.parse_args()

    if args.platforms.strip():
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    else:
        # Heavy GoFundMe last; prioritize global/discover platforms first
        all_p = list_platforms()
        priority = [
            "islamicrelief_ca",
            "launchgood",
            "globalgiving",
            "ketto",
            "mchanga",
            "backabuddy",
            "giveasia",
            "thundafund",
            "justgiving",
            "givebutter",
        ]
        ordered = [p for p in priority if p in all_p]
        ordered += [p for p in all_p if p not in ordered]
        platforms = ordered

    logger.info(
        "Scrape loop: %d platforms, interval=%ds, db=%s",
        len(platforms),
        args.interval,
        os.getenv("DB_PATH", str(ROOT / "givefund.db")),
    )

    cycle = 0
    while True:
        cycle += 1
        logger.info("========== cycle %d ==========", cycle)
        started = time.time()
        results: dict[str, bool] = {}
        for platform in platforms:
            results[platform] = run_platform(platform)
        elapsed = time.time() - started
        ok = sum(1 for v in results.values() if v)
        logger.info(
            "Cycle %d done in %.0fs: %d/%d platforms succeeded",
            cycle,
            elapsed,
            ok,
            len(platforms),
        )
        if args.once:
            break
        logger.info("Sleeping %ds until next cycle…", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
