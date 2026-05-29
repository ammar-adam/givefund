"""Short-lived in-memory cache for search results."""

from __future__ import annotations

import os
import time
from typing import Any

TTL_SEC = int(os.getenv("SEARCH_CACHE_TTL_SEC", "300"))


def _key(query: str, platform: str | None = None) -> str:
    p = (platform or "").strip().lower()
    return f"{query.strip().lower()}|{p}"


_store: dict[str, tuple[float, dict[str, Any]]] = {}


def get_cached(query: str, *, platform: str | None = None) -> dict[str, Any] | None:
    entry = _store.get(_key(query, platform))
    if not entry:
        return None
    ts, payload = entry
    if time.time() - ts > TTL_SEC:
        _store.pop(_key(query, platform), None)
        return None
    return payload


def set_cached(query: str, payload: dict[str, Any], *, platform: str | None = None) -> None:
    _store[_key(query, platform)] = (time.time(), payload)
