import logging
import os
import time

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
    PlatformsResponse,
    SortBy,
    StatsResponse,
)


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GiveFund API")


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
