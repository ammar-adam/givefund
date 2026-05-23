import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import db
from models import Campaign, CampaignsResponse, CategoriesResponse, HealthResponse, SortBy


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GiveFund API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/campaigns", response_model=CampaignsResponse)
async def list_campaigns(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    sort_by: SortBy = Query(default="most_needed"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> CampaignsResponse:
    """Return campaigns filtered by search, category, sort, and pagination."""

    try:
        campaigns, total, pages = await db.get_campaigns(
            search=search,
            category=category,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        return CampaignsResponse(campaigns=campaigns, total=total, page=page, pages=pages)
    except Exception as exc:
        logger.exception("Failed to list campaigns with search=%r category=%r", search, category)
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
