#!/usr/bin/env python3
"""
Bootstrap 10k+ campaigns — optimized volume ingest.

  cd scraper
  python scale_ingest.py              # full scale (GFM Algolia + boost + OpenCollective + rest)
  python scale_ingest.py --gfm-only   # fastest path to 10k GoFundMe rows
  python scale_ingest.py --target 15000

Requires: playwright install chromium (for Algolia key capture if env keys missing).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time

from db import count_campaigns, create_table, get_connection, persist_campaigns_batch
from platforms import ALL_PLATFORMS, PLATFORM_SCRAPERS
from platforms.gofundme import scrape_gofundme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("scale_ingest")

# Force scale defaults unless user already set them
os.environ.setdefault("GFM_ALGOLIA_ONLY", "true")
os.environ.setdefault("GFM_MAX_ALGOLIA_PAGES", "100")
os.environ.setdefault("GFM_BOOST_PAGES", "12")
os.environ.setdefault("DISCOVER_MAX_CAMPAIGNS", "200")


async def _save(conn, campaigns: list[dict], label: str) -> int:
    if not campaigns:
        logger.warning("[%s] 0 campaigns to save", label)
        return 0
    saved = await persist_campaigns_batch(conn, campaigns)
    total = await count_campaigns(conn)
    logger.info("[%s] saved=%d db_total=%d", label, saved, total)
    return total


async def run_scale(
    *,
    target: int,
    gfm_only: bool,
    skip_opencollective: bool,
    parallel: int,
) -> dict:
    started = time.perf_counter()
    summary: dict = {"target": target, "phases": {}}

    async with get_connection() as conn:
        await create_table(conn)
        before = await count_campaigns(conn)
        summary["before"] = before
        logger.info("=== Scale ingest start — %d campaigns in DB (target %d) ===", before, target)

        # Phase 1: GoFundMe Algolia (main volume)
        os.environ["GFM_ALGOLIA_ONLY"] = "true"
        gfm_rows = await scrape_gofundme()
        total = await _save(conn, gfm_rows, "gofundme")
        summary["phases"]["gofundme"] = {"scraped": len(gfm_rows), "db_total": total}

        if total >= target and gfm_only:
            summary["after"] = total
            summary["elapsed_sec"] = time.perf_counter() - started
            return summary

        # Phase 2: Open Collective (API, no key)
        if not skip_opencollective and not gfm_only:
            try:
                from platforms.opencollective import scrape_opencollective

                oc_rows = await scrape_opencollective()
                total = await _save(conn, oc_rows, "opencollective")
                summary["phases"]["opencollective"] = {
                    "scraped": len(oc_rows),
                    "db_total": total,
                }
            except Exception as exc:
                logger.error("opencollective phase failed: %s", exc)
                summary["phases"]["opencollective"] = {"error": str(exc)}

        if total >= target or gfm_only:
            summary["after"] = await count_campaigns(conn)
            summary["elapsed_sec"] = time.perf_counter() - started
            return summary

        # Phase 3: other wired platforms (parallel)
        from live_runner import run_live_cycle

        rest = [p for p in ALL_PLATFORMS if p not in ("gofundme", "opencollective")]
        cycle = await run_live_cycle(platforms=rest, parallel=parallel)
        summary["phases"]["other_platforms"] = cycle
        total = cycle.get("total_campaigns", await count_campaigns(conn))

        summary["after"] = total
        summary["elapsed_sec"] = time.perf_counter() - started
        logger.info(
            "=== Scale ingest done in %.0fs — %d -> %d campaigns ===",
            summary["elapsed_sec"],
            before,
            total,
        )
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap 10k+ campaigns")
    parser.add_argument("--target", type=int, default=int(os.getenv("SCALE_TARGET", "10000")))
    parser.add_argument("--gfm-only", action="store_true", help="Only GoFundMe Algolia (fastest)")
    parser.add_argument("--skip-opencollective", action="store_true")
    parser.add_argument("--parallel", type=int, default=int(os.getenv("SCRAPE_PARALLEL", "4")))
    args = parser.parse_args()

    summary = asyncio.run(
        run_scale(
            target=args.target,
            gfm_only=args.gfm_only,
            skip_opencollective=args.skip_opencollective,
            parallel=args.parallel,
        )
    )

    after = summary.get("after", 0)
    print(f"\n{'=' * 50}")
    print(f"  Campaigns in DB: {after:,}  (target {args.target:,})")
    if after >= args.target:
        print("  Target reached.")
    else:
        print("  Set GFM_ALGOLIA_APP_ID + GFM_ALGOLIA_API_KEY in .env for faster reruns.")
        print("  Or re-run: python scale_ingest.py --gfm-only")
    print(f"{'=' * 50}\n")

    sys.exit(0 if after >= args.target else 1)


if __name__ == "__main__":
    main()
