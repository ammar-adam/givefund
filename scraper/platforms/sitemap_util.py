"""Fetch campaign URLs from XML sitemaps (when sites expose them)."""

from __future__ import annotations

import logging
import re
from typing import Iterable
from xml.etree import ElementTree

import httpx

from platforms.base import USER_AGENT

logger = logging.getLogger(__name__)

_LOC_RE = re.compile(r"<loc>\s*([^<]+?)\s*</loc>", re.I)
_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def fetch_sitemap_locs(
    sitemap_url: str,
    *,
    timeout: float = 30.0,
    max_locs: int = 500,
) -> list[str]:
    """Return <loc> entries from a sitemap or sitemap index (one level of index)."""

    headers = {"User-Agent": USER_AGENT}
    locs: list[str] = []
    try:
        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            resp = await client.get(sitemap_url)
            resp.raise_for_status()
            text = resp.text
    except Exception as exc:
        logger.warning("sitemap fetch failed %s: %s", sitemap_url, exc)
        return []

    if "<sitemapindex" in text.lower():
        child_maps = _LOC_RE.findall(text)[:20]
        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            for child in child_maps:
                try:
                    r = await client.get(child)
                    r.raise_for_status()
                    locs.extend(_LOC_RE.findall(r.text))
                except Exception:
                    continue
    else:
        locs = _LOC_RE.findall(text)

    return locs[:max_locs]


def filter_urls(locs: Iterable[str], *substrings: str) -> list[str]:
    """Keep URLs containing any of the given substrings."""

    out: list[str] = []
    seen: set[str] = set()
    for loc in locs:
        url = loc.split("?")[0].strip()
        if not url or url in seen:
            continue
        if any(s in url for s in substrings):
            seen.add(url)
            out.append(url)
    return out
