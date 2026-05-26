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
    location: str | None = None
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


class PlatformInfo(BaseModel):
    """A supported crowdfunding platform."""

    id: str
    label: str


class PlatformsResponse(BaseModel):
    """Available campaign platforms."""

    platforms: list[str]


class PlatformCatalogResponse(BaseModel):
    """All platforms GiveFund can index."""

    platforms: list[PlatformInfo]
    count: int


class StatsResponse(BaseModel):
    """Aggregate campaign statistics."""

    total_campaigns: int
    total_raised: float
    platforms: list[str]
    last_scraped: str | None = None


class HealthResponse(BaseModel):
    """Service health and database status."""

    status: str
    campaign_count: int


SortBy = Literal["most_needed", "almost_there", "newest"]


class CheckoutConfigResponse(BaseModel):
    """Whether Stripe Link checkout is available."""

    enabled: bool
    publishable_key: str | None = None
    default_tip_cents: int = 500
    min_tip_cents: int = 100
    max_tip_cents: int = 50_000


class LinkCheckoutRequest(BaseModel):
    """Start Stripe Checkout to enroll donor in Link via optional tip."""

    email: str = Field(min_length=3, max_length=320)
    amount_cents: int = Field(default=500, ge=100, le=50_000)
    success_url: str | None = None
    cancel_url: str | None = None
    campaign_id: int | None = Field(default=None, ge=1)


class LinkCheckoutResponse(BaseModel):
    """Redirect donor to Stripe-hosted checkout."""

    session_id: str
    url: str
