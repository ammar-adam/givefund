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
    last_ingest_at: str | None = None
    live_tracking: bool = True


class PlatformIngestStat(BaseModel):
    """Per-platform result from the latest ingest run."""

    platform: str
    scraped: int = 0
    saved: int = 0
    db_total: int = 0
    duration_sec: float = 0.0
    error: str | None = None


class LiveSearchResponse(BaseModel):
    """On-demand cross-platform search results (may include campaigns not yet in DB)."""

    query: str
    campaigns: list[Campaign]
    total: int
    live_count: int = 0
    cached_count: int = 0
    by_platform: dict[str, int] = {}
    persisted: int | None = None
    error: str | None = None


class IngestStatusResponse(BaseModel):
    """Live scrape pipeline status for the UI."""

    live_tracking: bool = True
    refresh_interval_sec: int = 1800
    run_id: int | None = None
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    total_scraped: int = 0
    total_saved: int = 0
    total_campaigns: int = 0
    is_running: bool = False
    platforms: list[PlatformIngestStat] = []


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
