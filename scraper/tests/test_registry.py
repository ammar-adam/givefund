"""Scraper registry smoke tests."""

import sys
from pathlib import Path

SCRAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRAPER_ROOT))

from platforms import ALL_PLATFORMS, PLATFORM_SCRAPERS  # noqa: E402


def test_all_platforms_have_scrapers():
    assert len(ALL_PLATFORMS) >= 18
    for name in ALL_PLATFORMS:
        assert name in PLATFORM_SCRAPERS
        assert callable(PLATFORM_SCRAPERS[name])


def test_global_platforms_registered():
    for required in (
        "gofundme",
        "launchgood",
        "islamicrelief_ca",
        "ketto",
        "backabuddy",
        "milaap",
        "globalgiving",
    ):
        assert required in PLATFORM_SCRAPERS
