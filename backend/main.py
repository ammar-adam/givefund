import logging
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import db
from models import (
    Campaign,
    CampaignsResponse,
    CategoriesResponse,
    HealthResponse,
    IngestStatusResponse,
    LiveSearchResponse,
    PlatformCatalogResponse,
    PlatformInfo,
    PlatformsResponse,
    SortBy,
    StatsResponse,
)
from platforms_catalog import PLATFORM_CATALOG, SUPPORTED_PLATFORM_COUNT
from search_bridge import run_live_search_subprocess


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _sync_database_from_url() -> None:
    """Download givefund.db when DB_DOWNLOAD_URL is configured."""
    script = Path(__file__).resolve().parents[1] / "scripts" / "download_db.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], check=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup hooks for production database sync."""
    _sync_database_from_url()
    yield


app = FastAPI(title="GiveFund API", lifespan=lifespan)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration for every request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return clear 422 messages for invalid query parameters."""

    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors
    )
    return JSONResponse(status_code=422, content={"detail": detail or "Invalid request"})


def _campaign_from_row_dict(row: dict, row_id: int) -> Campaign:
    """Build API Campaign from scraper dict (synthetic id when not in DB)."""
    goal = float(row.get("goal_amount") or 0)
    raised = float(row.get("raised_amount") or 0)
    gap = max(goal - raised, 0.0) if goal > 0 else 0.0
    pct = min(100.0, round(100.0 * raised / goal, 1)) if goal > 0 else 0.0
    return Campaign(
        id=row_id,
        title=row.get("title"),
        story_snippet=row.get("story_snippet"),
        photo_url=row.get("photo_url"),
        goal_amount=row.get("goal_amount"),
        raised_amount=row.get("raised_amount"),
        funding_gap=gap,
        pct_funded=pct,
        platform=row.get("platform") or "unknown",
        campaign_url=row["campaign_url"],
        category=row.get("category"),
        location=row.get("location"),
        scraped_at=row.get("scraped_at"),
    )


@app.get("/search/live", response_model=LiveSearchResponse)
async def search_live(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=50, ge=5, le=100),
    persist: bool = Query(default=False),
    merge_db: bool = Query(default=True),
) -> LiveSearchResponse:
    """
    Live index: scrape/search all wired platforms for this query and return results.
    Surfaces campaigns even if they were never bulk-ingested.
    """
    try:
        raw = await run_live_search_subprocess(q, limit=limit, persist=persist)
    except Exception as exc:
        logger.exception("live search failed")
        raise HTTPException(status_code=500, detail="Live search failed") from exc

    live_rows = raw.get("campaigns") or []
    by_platform = raw.get("by_platform") or {}
    merged: dict[str, Campaign] = {}

    if merge_db:
        try:
            db_rows, _, _ = await db.get_campaigns(
                search=q, page=1, page_size=limit, sort_by="most_needed"
            )
            for c in db_rows:
                merged[c.campaign_url] = c
        except Exception:
            logger.warning("DB merge for live search skipped")

    base_id = 900_000_000
    for i, row in enumerate(live_rows):
        url = row.get("campaign_url")
        if not url:
            continue
        synthetic_id = base_id + (abs(hash(url)) % 99_000_000)
        merged[url] = _campaign_from_row_dict(row, synthetic_id)

    campaigns = list(merged.values())[:limit]
    return LiveSearchResponse(
        query=q,
        campaigns=campaigns,
        total=len(campaigns),
        live_count=len(live_rows),
        cached_count=max(0, len(campaigns) - len(live_rows)),
        by_platform=by_platform,
        persisted=raw.get("saved"),
        error=raw.get("error"),
    )


@app.get("/campaigns", response_model=CampaignsResponse)
async def list_campaigns(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    sort_by: SortBy = Query(default="most_needed"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> CampaignsResponse:
    """Return campaigns filtered by search, category, platform, sort, and pagination."""

    try:
        campaigns, total, pages = await db.get_campaigns(
            search=search,
            category=category,
            platform=platform,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        return CampaignsResponse(campaigns=campaigns, total=total, page=page, pages=pages)
    except Exception as exc:
        logger.exception("Failed to list campaigns")
        raise HTTPException(status_code=500, detail="Failed to list campaigns") from exc


@app.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: int) -> Campaign:
    """Return one campaign by id."""

    try:
        campaign = await db.get_campaign(campaign_id)
    except Exception as exc:
        logger.exception("Failed to fetch campaign id=%s", campaign_id)
        raise HTTPException(status_code=500, detail="Failed to fetch campaign") from exc

    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@app.get("/categories", response_model=CategoriesResponse)
async def list_categories() -> CategoriesResponse:
    """Return distinct categories present in the campaign database."""

    try:
        return CategoriesResponse(categories=await db.get_categories())
    except Exception as exc:
        logger.exception("Failed to list categories")
        raise HTTPException(status_code=500, detail="Failed to list categories") from exc


@app.get("/platforms", response_model=PlatformsResponse)
async def list_platforms() -> PlatformsResponse:
    """Return distinct platforms present in the campaign database."""

    try:
        return PlatformsResponse(platforms=await db.get_platforms())
    except Exception as exc:
        logger.exception("Failed to list platforms")
        raise HTTPException(status_code=500, detail="Failed to list platforms") from exc


@app.get("/platforms/catalog", response_model=PlatformCatalogResponse)
async def platform_catalog() -> PlatformCatalogResponse:
    """Return every platform GiveFund supports (independent of DB rows)."""

    return PlatformCatalogResponse(
        platforms=[PlatformInfo(**entry) for entry in PLATFORM_CATALOG],
        count=SUPPORTED_PLATFORM_COUNT,
    )


@app.get("/ingest/status", response_model=IngestStatusResponse)
async def ingest_status() -> IngestStatusResponse:
    """Live scrape pipeline status — when data was last refreshed."""

    try:
        data = await db.get_ingest_status()
        return IngestStatusResponse(**data)
    except Exception as exc:
        logger.exception("Failed to read ingest status")
        raise HTTPException(status_code=500, detail="Failed to read ingest status") from exc


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Return aggregate campaign statistics."""

    try:
        data = await db.get_stats()
        return StatsResponse(**data)
    except Exception as exc:
        logger.exception("Failed to read stats")
        raise HTTPException(status_code=500, detail="Failed to read stats") from exc


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return API health and campaign count."""

    try:
        return HealthResponse(status="ok", campaign_count=await db.get_campaign_count())
    except Exception as exc:
        logger.exception("Failed to read health status")
        raise HTTPException(status_code=500, detail="Failed to read health status") from exc


def get_port() -> int:
    """Return the configured server port."""

    return int(os.getenv("PORT", "8000"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=get_port(), reload=True)
