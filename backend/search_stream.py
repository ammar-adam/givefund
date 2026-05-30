"""SSE streaming wrapper for live search."""

from __future__ import annotations

import json
import logging
from typing import Any

from search_live import run_live_search as run_live_search_collect

logger = logging.getLogger(__name__)


async def stream_live_search_events(
    query: str,
    *,
    limit: int = 80,
    platforms: list[str] | None = None,
    persist: bool = False,
):
    """Async generator of SSE lines (data: {...}\\n\\n)."""
    from search_live import _import_scraper
    from search_live import run_live_search_stream

    _import_scraper()

    merged_for_persist: list[dict] = []

    try:
        async for event in run_live_search_stream(
            query,
            limit_per_platform=min(limit, 20),
            platforms=platforms,
        ):
            if event.get("type") == "platform":
                merged_for_persist.extend(event.get("campaigns") or [])
            yield f"data: {json.dumps(event, default=str)}\n\n"

            if event.get("type") == "done" and persist:
                from search_live import _persist_background
                import asyncio

                to_save = event.get("campaigns") or merged_for_persist
                if to_save:
                    asyncio.create_task(_persist_background(to_save))
                yield f"data: {json.dumps({'type': 'persist_queued'})}\n\n"

    except Exception as exc:
        logger.exception("stream search failed")
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)[:200]})}\n\n"

        summary = await run_live_search_collect(
            query, limit=limit, platforms=platforms, persist=False
        )
        yield f"data: {json.dumps({'type': 'done', **summary}, default=str)}\n\n"
