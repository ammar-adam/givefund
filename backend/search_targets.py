"""List platforms participating in live search."""

from __future__ import annotations

import sys
from pathlib import Path

SCRAPER_DIR = Path(__file__).resolve().parents[1] / "scraper"


def get_search_targets() -> dict:
    path = str(SCRAPER_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
    from live_search import API_PLATFORM_IDS, discover_search_configs

    http_ids = [c.platform for c in discover_search_configs()]
    return {
        "api": list(API_PLATFORM_IDS),
        "http": http_ids,
        "total": len(API_PLATFORM_IDS) + len(http_ids),
    }
