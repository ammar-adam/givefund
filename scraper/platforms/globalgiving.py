"""GlobalGiving projects via official API (requires GLOBALGIVING_API_KEY)."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.globalgiving.org/api/public/projectservice"
PLATFORM = "globalgiving"


def _parse_money(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(text).replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _project_to_campaign(project: dict[str, Any]) -> dict:
    goal = _parse_money(project.get("goal"))
    raised = _parse_money(project.get("funding"))
    title = project.get("title") or "GlobalGiving project"
    summary = project.get("shortDescription") or project.get("longDescription") or ""
    if len(summary) > 500:
        summary = summary[:497] + "..."
    country = project.get("country") or project.get("iso3166CountryCode")
    themes = project.get("themes", {}).get("theme", [])
    theme_name = ""
    if isinstance(themes, list) and themes:
        theme_name = themes[0].get("name", "") if isinstance(themes[0], dict) else str(themes[0])
    elif isinstance(themes, dict):
        theme_name = themes.get("name", "")
    category = "community"
    lower = f"{title} {summary} {theme_name}".lower()
    for key in ("medical", "health", "education", "emergency", "water", "food"):
        if key in lower:
            category = key if key != "health" else "medical"
            break
    project_id = project.get("id")
    url = project.get("projectLink") or (
        f"https://www.globalgiving.org/projects/{project_id}/" if project_id else None
    )
    image = None
    imgs = project.get("image", project.get("imageLink"))
    if isinstance(imgs, dict):
        image = imgs.get("imagelink") or imgs.get("imageLink")
    elif isinstance(imgs, list) and imgs:
        image = imgs[0].get("imagelink") if isinstance(imgs[0], dict) else imgs[0]
    elif isinstance(imgs, str):
        image = imgs

    return {
        "title": title,
        "story_snippet": summary or None,
        "photo_url": image,
        "goal_amount": goal,
        "raised_amount": raised,
        "platform": PLATFORM,
        "campaign_url": url or f"https://www.globalgiving.org/donate/{project_id}/",
        "category": category,
        "location": country,
    }


async def _scrape_html_fallback() -> list[dict]:
    """Discover projects from public listing when API key is missing."""

    from platforms.discover import DiscoverConfig, scrape_discover

    cfg = DiscoverConfig(
        platform=PLATFORM,
        base_url="https://www.globalgiving.org",
        start_urls=("https://www.globalgiving.org/projects/",),
        link_markers=("/projects/",),
        card_selectors=("a[href*='/projects/']", "article"),
        max_campaigns=40,
    )
    return await scrape_discover(cfg)


async def scrape_globalgiving(max_pages: int = 50) -> list[dict]:
    """Paginate active projects (10 per page) until max_pages or no more results."""

    api_key = os.getenv("GLOBALGIVING_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            "[%s] GLOBALGIVING_API_KEY not set — using HTML discover fallback",
            PLATFORM,
        )
        return await _scrape_html_fallback()

    campaigns: list[dict] = []
    next_id: str | None = None
    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(max_pages):
            params: dict[str, str] = {"api_key": api_key}
            if next_id:
                params["nextProjectId"] = next_id
            url = f"{API_BASE}/all/projects/active"
            try:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("[%s] API page %d failed: %s", PLATFORM, page, exc)
                break

            projects = data.get("projects", {}).get("project", [])
            if isinstance(projects, dict):
                projects = [projects]
            if not projects:
                break

            for proj in projects:
                if not isinstance(proj, dict):
                    continue
                try:
                    campaign = _project_to_campaign(proj)
                    if campaign.get("campaign_url"):
                        campaigns.append(campaign)
                except Exception as exc:
                    logger.error("[%s] parse project: %s", PLATFORM, exc)

            next_id = data.get("nextProjectId")
            has_more = str(data.get("hasNext", "false")).lower() == "true"
            logger.info(
                "[%s] page %d: +%d (total %d) hasNext=%s",
                PLATFORM,
                page,
                len(projects),
                len(campaigns),
                has_more,
            )
            if not has_more or not next_id:
                break

    if len(campaigns) < 5:
        logger.info("[%s] API sparse — trying HTML fallback", PLATFORM)
        seen = {c["campaign_url"] for c in campaigns}
        for row in await _scrape_html_fallback():
            if row["campaign_url"] not in seen:
                campaigns.append(row)
                seen.add(row["campaign_url"])

    logger.info("[%s] total campaigns: %d", PLATFORM, len(campaigns))
    return campaigns


SEARCH_URL = (
    "https://api.globalgiving.org/api/public/services/search/projects/summary"
)


async def search_globalgiving(query: str, *, max_results: int = 40) -> list[dict]:
    """Keyword search via official API (requires GLOBALGIVING_API_KEY)."""

    api_key = os.getenv("GLOBALGIVING_API_KEY", "").strip()
    if not api_key or not query.strip():
        return []

    campaigns: list[dict] = []
    start = 0
    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(campaigns) < max_results:
            params = {
                "api_key": api_key,
                "q": query.strip(),
                "start": str(start),
            }
            try:
                resp = await client.get(SEARCH_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("[%s] search %r failed: %s", PLATFORM, query, exc)
                break

            projects = data.get("projects", {}).get("project", [])
            if isinstance(projects, dict):
                projects = [projects]
            if not projects:
                break

            for proj in projects:
                if not isinstance(proj, dict):
                    continue
                try:
                    campaign = _project_to_campaign(proj)
                    if campaign.get("campaign_url"):
                        campaigns.append(campaign)
                except Exception as exc:
                    logger.error("[%s] search parse: %s", PLATFORM, exc)

            start += len(projects)
            if len(projects) < 10:
                break

    logger.info("[%s] search %r -> %d", PLATFORM, query, len(campaigns))
    return campaigns[:max_results]
