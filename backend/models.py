from typing import Literal

from pydantic import BaseModel, Field


class Campaign(BaseModel):
    """API representation of a crowdfunding campaign."""

    id: int
    title: str | None = None
    story_snippet: str | None = None
    photo_url: str | None = None
    goal_amount: float | None = None
    raised_amount: float | None = None
    funding_gap: float = 0.0
    pct_funded: float = 0.0
    platform: str = "gofundme"
    campaign_url: str
    category: str | None = None
    scraped_at: str | None = None


class CampaignsResponse(BaseModel):
    """Paginated response for campaign search results."""

    campaigns: list[Campaign]
    total: int
    page: int = Field(ge=1)
    pages: int = Field(ge=0)


class CategoriesResponse(BaseModel):
    """Available campaign categories."""

    categories: list[str]


class HealthResponse(BaseModel):
    """Service health and database status."""

    status: str
    campaign_count: int


SortBy = Literal["most_needed", "almost_there", "newest"]
