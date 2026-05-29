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
    platforms_indexed: int = 0
    platforms_supported: int = 0
    last_scraped: str | None = None
    last_ingest_at: str | None = None
    live_tracking: bool = True


class WalletConfigResponse(BaseModel):
    """Whether saved-card setup via Stripe is available."""

    enabled: bool
    publishable_key: str | None = None
    google_oauth_enabled: bool = False
    google_client_id: str | None = None


class WalletSetupRequest(BaseModel):
    """Start Stripe Checkout (setup mode) to save a card — no charge."""

    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=120)
    success_url: str | None = None
    cancel_url: str | None = None


class WalletSetupResponse(BaseModel):
    """Redirect to Stripe-hosted setup."""

    session_id: str
    url: str
    stripe_customer_id: str | None = None


class WalletCompleteRequest(BaseModel):
    """Finalize wallet after Stripe redirect."""

    session_id: str = Field(min_length=8, max_length=200)


class WalletCompleteResponse(BaseModel):
    """Donor profile after successful card save."""

    email: str
    has_saved_card: bool
    display_name: str | None = None
    wallet_saved_at: str | None = None
    link_ready: bool = False


class DonorProfileResponse(BaseModel):
    """Saved donor identity for checkout prefill."""

    email: str
    has_saved_card: bool = False
    display_name: str | None = None
    wallet_saved_at: str | None = None
    link_ready: bool = False


class GoogleAuthRequest(BaseModel):
    """Google Sign-In credential (ID token)."""

    credential: str = Field(min_length=20)


class GoogleAuthResponse(BaseModel):
    """Verified Google identity — use email for wallet setup."""

    email: str
    display_name: str | None = None
    profile: DonorProfileResponse


class CheckoutAssistResponse(BaseModel):
    """Express Give — optimized outbound checkout for one campaign."""

    campaign_id: int
    title: str | None = None
    platform: str
    donate_url: str
    link_likely: bool = False
    email_prefill_supported: bool = False
    prefill_fields: list[str] = []
    donor_email: str | None = None
    donor_name: str | None = None
    wallet_saved: bool = False
    checkout_note: str
    steps_saved_estimate: str
    cannot_token_charge: bool = True
    cannot_token_charge_reason: str


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
