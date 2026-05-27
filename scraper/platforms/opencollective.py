"""Open Collective public GraphQL — 600k+ accounts; paginate + keyword search."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.opencollective.com/graphql/v2"
PLATFORM = "opencollective"
DEFAULT_LIMIT = int(os.getenv("OC_PAGE_SIZE", "100"))
MAX_PAGES = int(os.getenv("OC_MAX_PAGES", "80"))
SEARCH_TERMS = tuple(
    t.strip()
    for t in os.getenv(
        "OC_SEARCH_TERMS",
        "medical,emergency,relief,education,community,charity,ukraine,gaza,cancer,disaster",
    ).split(",")
    if t.strip()
)

_ACCOUNTS_QUERY = """
query Accounts($limit: Int!, $offset: Int!, $searchTerm: String) {
  accounts(limit: $limit, offset: $offset, searchTerm: $searchTerm) {
    totalCount
    nodes {
      id
      name
      slug
      description
      tags
      imageUrl
      stats {
        totalAmountReceived { value currency }
      }
    }
  }
}
"""


def _node_to_campaign(node: dict[str, Any]) -> dict | None:
    slug = node.get("slug")
    if not slug:
        return None
    name = (node.get("name") or slug).strip()
    desc = (node.get("description") or "").strip()
    if len(desc) > 500:
        desc = desc[:497] + "..."
    stats = node.get("stats") or {}
    received = (stats.get("totalAmountReceived") or {}).get("value")
    raised = float(received) if received is not None else None
    tags = node.get("tags") or []
    tag_text = " ".join(tags) if isinstance(tags, list) else ""
    category = "community"
    lower = f"{name} {desc} {tag_text}".lower()
    for key in ("medical", "education", "emergency"):
        if key in lower:
            category = key
            break

    return {
        "title": name,
        "story_snippet": desc or None,
        "photo_url": node.get("imageUrl"),
        "goal_amount": None,
        "raised_amount": raised,
        "platform": PLATFORM,
        "campaign_url": f"https://opencollective.com/{slug}",
        "category": category,
        "location": None,
    }


async def _fetch_page(
    client: httpx.AsyncClient,
    offset: int,
    search_term: str | None,
) -> list[dict]:
    variables: dict[str, Any] = {"limit": DEFAULT_LIMIT, "offset": offset}
    if search_term:
        variables["searchTerm"] = search_term
    resp = await client.post(
        GRAPHQL_URL,
        json={"query": _ACCOUNTS_QUERY, "variables": variables},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(str(data["errors"][:1]))
    nodes = (data.get("data") or {}).get("accounts", {}).get("nodes") or []
    out: list[dict] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        row = _node_to_campaign(node)
        if row:
            out.append(row)
    return out


async def scrape_opencollective() -> list[dict]:
    """Paginate Open Collective accounts (search terms + recent offset browse)."""
    campaigns: dict[str, dict] = {}
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(headers=headers) as client:
        for term in [None, *SEARCH_TERMS]:
            label = term or "browse"
            for page in range(MAX_PAGES):
                offset = page * DEFAULT_LIMIT
                try:
                    rows = await _fetch_page(client, offset, term)
                except Exception as exc:
                    logger.error("[opencollective] %s page %d: %s", label, page, exc)
                    break
                if not rows:
                    break
                for row in rows:
                    campaigns[row["campaign_url"]] = row
                logger.info(
                    "[opencollective] %s page %d +%d (unique %d)",
                    label,
                    page,
                    len(rows),
                    len(campaigns),
                )
                if len(rows) < DEFAULT_LIMIT:
                    break

    result = list(campaigns.values())
    logger.info("[opencollective] total unique: %d", len(result))
    return result
