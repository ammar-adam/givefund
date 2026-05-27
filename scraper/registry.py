"""Load platform scrape/search metadata from platform_registry.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

ScrapeMethod = Literal[
    "algolia",
    "official_api",
    "search_url",
    "discover",
    "blocked",
    "org_only",
]


@dataclass(frozen=True)
class PlatformEntry:
    id: str
    name: str
    region: str
    scrape_method: ScrapeMethod
    search_method: str | None = None
    env_keys: tuple[str, ...] = ()
    search_url_template: str | None = None
    discover_urls: tuple[str, ...] = ()
    link_markers: tuple[str, ...] = ()
    base_url: str | None = None
    notes: str = ""


REGISTRY_PATH = Path(__file__).resolve().parent / "platform_registry.json"


@lru_cache(maxsize=1)
def load_registry() -> list[PlatformEntry]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries: list[PlatformEntry] = []
    for row in raw.get("platforms", []):
        entries.append(
            PlatformEntry(
                id=row["id"],
                name=row.get("name", row["id"]),
                region=row.get("region", "global"),
                scrape_method=row.get("scrape_method", "discover"),
                search_method=row.get("search_method"),
                env_keys=tuple(row.get("env_keys", [])),
                search_url_template=row.get("search_url_template"),
                discover_urls=tuple(row.get("discover_urls", [])),
                link_markers=tuple(row.get("link_markers", [])),
                base_url=row.get("base_url"),
                notes=row.get("notes", ""),
            )
        )
    return entries


def implemented_platform_ids() -> set[str]:
    from platforms import ALL_PLATFORMS

    return set(ALL_PLATFORMS)


def live_search_platforms() -> list[PlatformEntry]:
    """Platforms we can query on-demand when a user searches."""
    done = implemented_platform_ids()
    out: list[PlatformEntry] = []
    for entry in load_registry():
        if entry.id not in done:
            continue
        if entry.scrape_method in ("algolia", "official_api"):
            out.append(entry)
        elif entry.search_url_template:
            out.append(entry)
    return out
