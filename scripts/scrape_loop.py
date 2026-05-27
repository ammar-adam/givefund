#!/usr/bin/env python3
"""
Continuous live ingestion for GiveFund.

Runs scraper/live_runner.py (parallel platforms, batch DB writes).
Default: every 30 minutes. Production: set LIVE_SCRAPE=true in start_prod.sh.

    python scripts/scrape_loop.py
    python scripts/scrape_loop.py --once
    python scripts/scrape_loop.py --interval 900
"""

from __future__ import annotations

import argparse
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


def run_live_once(parallel: int) -> int:
    env = os.environ.copy()
    env.setdefault("DB_PATH", str(ROOT / "givefund.db"))
    cmd = [
        sys.executable,
        "live_runner.py",
        "--once",
        "--parallel",
        str(parallel),
    ]
    logger.info("Starting live ingest cycle (parallel=%s)", parallel)
    result = subprocess.run(
        cmd,
        cwd=SCRAPER_DIR,
        env=env,
        timeout=int(os.getenv("SCRAPE_CYCLE_TIMEOUT", "7200")),
    )
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="GiveFund live scrape loop")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("SCRAPE_INTERVAL", "1800")),
        help="Seconds between live cycles (default: 1800 = 30 min)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle then exit",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=int(os.getenv("SCRAPE_PARALLEL", "4")),
        help="Parallel platform workers (excludes GoFundMe)",
    )
    args = parser.parse_args()

    logger.info(
        "Live scrape loop — interval=%ds db=%s",
        args.interval,
        os.getenv("DB_PATH", str(ROOT / "givefund.db")),
    )

    cycle = 0
    while True:
        cycle += 1
        logger.info("========== live cycle %d ==========", cycle)
        started = time.time()
        code = run_live_once(args.parallel)
        logger.info(
            "Cycle %d finished in %.0fs (exit %d)",
            cycle,
            time.time() - started,
            code,
        )
        if args.once:
            break
        logger.info("Sleeping %ds…", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
