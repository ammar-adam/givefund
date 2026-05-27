"""Invoke scraper/live_search.py from the API (Playwright runs in scraper env)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"
SEARCH_TIMEOUT_SEC = int(os.getenv("LIVE_SEARCH_TIMEOUT_SEC", "120"))


async def run_live_search_subprocess(
    query: str,
    *,
    limit: int = 50,
    persist: bool = False,
) -> dict:
    """Run live cross-platform search; returns parsed JSON from live_search.py."""
    cmd = [
        sys.executable,
        "live_search.py",
        "--q",
        query,
        "--json",
        "--limit",
        str(limit),
    ]
    if persist:
        cmd.append("--persist")

    env = os.environ.copy()
    env.setdefault("DB_PATH", str(Path(__file__).resolve().parents[1] / "givefund.db"))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(SCRAPER_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=SEARCH_TIMEOUT_SEC
        )
    except asyncio.TimeoutError:
        logger.error("live search timed out after %ss for %r", SEARCH_TIMEOUT_SEC, query)
        return {"query": query, "campaigns": [], "by_platform": {}, "total": 0, "error": "timeout"}

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:500]
        logger.error("live_search failed rc=%s: %s", proc.returncode, err)
        return {"query": query, "campaigns": [], "by_platform": {}, "total": 0, "error": err}

    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        logger.error("live_search invalid JSON: %s", exc)
        return {"query": query, "campaigns": [], "by_platform": {}, "total": 0, "error": "invalid_json"}
