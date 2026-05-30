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
from fastapi.responses import JSONResponse, StreamingResponseh
from starlette.middleware.base import BaseHTTPMiddleware

import db
from models import (
    Campaign,
    CampaignsResponse,
    CategoriesResponse,
    CheckoutAssistResponse,
    DonorProfileResponse,
    GoogleAuthRequest,
    GoogleAuthResponse,
    HealthResponse,
    IngestStatusResponse,
    LiveSearchResponse,
    PlatformCatalogResponse,
    WalletCompleteRequest,
    WalletCompleteResponse,
    WalletConfigResponse,
    WalletSetupRequest,
    WalletSetupResponse,
    PlatformInfo,
    PlatformsResponse,
    SortBy,
    StatsResponse,
)
from platforms_catalog import PLATFORM_CATALOG, SUPPORTED_PLATFORM_COUNT
from search_bridge import run_live_search_subprocess
from search_fast import run_fast_search
from search_live import run_live_search as run_live_search_inprocess
from search_cache import get_cached, set_cached
from search_stream import stream_live_search_events
from search_targets import get_search_targets
import donor_db
import google_oauth
import stripe_wallet
from deep_links import checkout_assist


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


@app.get("/search/fast", response_model=LiveSearchResponse)
async def search_fast(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=80, ge=5, le=100),
    merge_db: bool = Query(default=True),
) -> LiveSearchResponse:
    """Quick search: local index + GoFundMe Algolia (seconds, no full browser scrape)."""
    cache_key_platform = None
    cached = get_cached(q, platform=cache_key_platform)
    if cached:
        raw = cached
    else:
        try:
            raw = await run_fast_search(q, limit=limit)
            set_cached(q, raw, platform=cache_key_platform)
        except Exception as exc:
            logger.exception("fast search failed")
            raise HTTPException(status_code=500, detail="Fast search failed") from exc

    merged: dict[str, Campaign] = {}
    if merge_db:
        db_rows, total_db, _ = await db.get_campaigns(
            search=q, category=None, platform=None, page=1, page_size=limit, sort_by="most_needed"
        )
        for c in db_rows:
            merged[c.campaign_url] = c
        _ = total_db

    base_id = 900_000_000
    for row in raw.get("campaigns") or []:
        url = row.get("campaign_url")
        if not url:
            continue
        merged[url] = _campaign_from_row_dict(row, base_id + (abs(hash(url)) % 99_000_000))

    campaigns = list(merged.values())[:limit]
    live_count = len(raw.get("campaigns") or [])
    return LiveSearchResponse(
        query=q,
        campaigns=campaigns,
        total=len(campaigns),
        live_count=live_count,
        cached_count=max(0, len(campaigns) - live_count),
        by_platform=raw.get("by_platform") or {},
        error=raw.get("error"),
    )


@app.get("/search/live", response_model=LiveSearchResponse)
async def search_live(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=80, ge=5, le=100),
    persist: bool = Query(default=True),
    merge_db: bool = Query(default=True),
    platform: str | None = Query(default=None, max_length=40),
) -> LiveSearchResponse:
    """
    On-demand cross-platform search: scrapes all wired platforms for this query.
    Called when a user searches — results are persisted by default for Give Now ids.
    """
    platforms = [platform] if platform else None
    cached = get_cached(q, platform=platform)
    if cached:
        raw = cached
    else:
        try:
            raw = await run_live_search_inprocess(
                q,
                limit=limit,
                platforms=platforms,
                persist=persist,
            )
            if raw.get("campaigns"):
                set_cached(q, raw, platform=platform)
        except Exception as exc:
            logger.exception("live search failed, trying subprocess fallback")
            try:
                raw = await run_live_search_subprocess(q, limit=limit, persist=persist)
            except Exception as sub_exc:
                logger.exception("live search subprocess fallback failed")
                raise HTTPException(status_code=500, detail="Live search failed") from sub_exc

    live_rows = raw.get("campaigns") or []
    by_platform = raw.get("by_platform") or {}
    merged: dict[str, Campaign] = {}

    if merge_db:
        try:
            db_rows, _, _ = await db.get_campaigns(
                search=q,
                page=1,
                page_size=limit,
                sort_by="most_needed",
                platform=platform,
            )
            for c in db_rows:
                merged[c.campaign_url] = c
        except Exception:
            logger.warning("DB merge for live search skipped")

    base_id = 900_000_000
    for row in live_rows:
        url = row.get("campaign_url")
        if not url:
            continue
        synthetic_id = base_id + (abs(hash(url)) % 99_000_000)
        merged[url] = _campaign_from_row_dict(row, synthetic_id)

    if persist and live_rows:
        urls = [r.get("campaign_url") for r in live_rows if r.get("campaign_url")]
        try:
            for c in await db.get_campaigns_by_urls(urls):
                merged[c.campaign_url] = c
        except Exception:
            logger.warning("Could not resolve persisted campaign ids")

    campaigns = list(merged.values())[:limit]
    return LiveSearchResponse(
        query=q,
        campaigns=campaigns,
        total=len(campaigns),
        live_count=len(live_rows),
        cached_count=max(0, len(campaigns) - len(live_rows)),
        by_platform=by_platform,
        persisted=raw.get("saved") or raw.get("persist_queued"),
        error=raw.get("error"),
    )


@app.get("/search/targets")
async def search_targets() -> dict:
    """Platforms queried during live search (for UI progress)."""
    try:
        return get_search_targets()
    except Exception as exc:
        logger.exception("search targets failed")
        raise HTTPException(status_code=500, detail="Could not list search targets") from exc


@app.get("/search/live/stream")
async def search_live_stream(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=80, ge=5, le=100),
    persist: bool = Query(default=True),
    platform: str | None = Query(default=None, max_length=40),
) -> StreamingResponse:
    """
    Server-Sent Events: campaigns arrive per platform as they finish (often < 10s to first batch).
    """
    platforms = [platform] if platform else None

    async def event_generator():
        merged_cache: dict[str, Any] = {"campaigns": [], "by_platform": {}}
        async for chunk in stream_live_search_events(
            q, limit=limit, platforms=platforms, persist=persist
        ):
            yield chunk
            if chunk.startswith("data: "):
                try:
                    import json as _json

                    payload = _json.loads(chunk[6:].strip())
                    if payload.get("type") == "platform":
                        merged_cache["campaigns"].extend(payload.get("campaigns") or [])
                        merged_cache["by_platform"][payload["platform"]] = payload.get(
                            "count", 0
                        )
                    elif payload.get("type") == "done":
                        set_cached(q, payload, platform=platform)
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/campaigns", response_model=CampaignsResponse)
async def list_campaigns(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    sort_by: SortBy = Query(default="most_needed"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=48, ge=1, le=100),
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


@app.get("/campaigns/{campaign_id}/checkout", response_model=CheckoutAssistResponse)
async def campaign_checkout(
    campaign_id: int,
    email: str | None = Query(default=None, max_length=320),
) -> CheckoutAssistResponse:
    """
    Express Give: lowest-friction donate URL for this campaign.
    Optional email prefill where platforms allow it; Link hint when likely.
    """
    campaign = await db.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    donor_name: str | None = None
    wallet_saved = False
    if email:
        profile = await donor_db.profile_response(email)
        donor_name = profile.get("display_name")
        wallet_saved = bool(profile.get("has_saved_card"))

    data = checkout_assist(
        platform=campaign.platform,
        campaign_url=campaign.campaign_url,
        campaign_id=campaign.id,
        title=campaign.title,
        donor_email=email,
        donor_name=donor_name,
        wallet_saved=wallet_saved,
    )
    return CheckoutAssistResponse(**data)


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


def _frontend_base_url() -> str:
    return os.getenv("GIVEFUND_FRONTEND_URL", "http://127.0.0.1:5500").rstrip("/")


@app.get("/wallet/config", response_model=WalletConfigResponse)
async def wallet_config() -> WalletConfigResponse:
    """Stripe setup-mode availability (save card, no charge) + Google OAuth."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip() or None
    return WalletConfigResponse(
        enabled=stripe_wallet.is_configured(),
        publishable_key=stripe_wallet.get_publishable_key(),
        google_oauth_enabled=google_oauth.is_configured(),
        google_client_id=client_id,
    )


@app.get("/wallet/profile", response_model=DonorProfileResponse)
async def wallet_profile(
    email: str = Query(min_length=3, max_length=320),
) -> DonorProfileResponse:
    """Return saved donor profile for checkout prefill."""
    return DonorProfileResponse(**await donor_db.profile_response(email))


@app.post("/wallet/oauth/google", response_model=GoogleAuthResponse)
async def wallet_google_oauth(body: GoogleAuthRequest) -> GoogleAuthResponse:
    """Verify Google Sign-In and store donor identity."""
    if not google_oauth.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID on the API.",
        )
    try:
        identity = google_oauth.verify_credential(body.credential)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("google oauth failed")
        raise HTTPException(status_code=502, detail="Google sign-in failed") from exc

    await donor_db.upsert_profile(
        email=identity["email"],
        display_name=identity.get("display_name") or None,
        google_sub=identity.get("google_sub") or None,
    )
    profile = await donor_db.profile_response(identity["email"])
    return GoogleAuthResponse(
        email=identity["email"],
        display_name=identity.get("display_name") or None,
        profile=DonorProfileResponse(**profile),
    )


@app.post("/wallet/setup", response_model=WalletSetupResponse)
async def wallet_setup(body: WalletSetupRequest) -> WalletSetupResponse:
    """Save payment method via Stripe Checkout (setup mode). No charge to the donor."""
    if not stripe_wallet.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Card save is not configured. Set STRIPE_SECRET_KEY on the API.",
        )
    base = _frontend_base_url()
    try:
        result = stripe_wallet.create_setup_session(
            email=body.email,
            display_name=body.display_name,
            success_url=body.success_url or f"{base}/wallet-success.html",
            cancel_url=body.cancel_url or f"{base}/wallet.html",
        )
        await donor_db.upsert_profile(
            email=body.email,
            display_name=body.display_name,
            stripe_customer_id=result.get("stripe_customer_id"),
        )
    except Exception as exc:
        logger.exception("wallet setup failed")
        raise HTTPException(status_code=502, detail="Could not start card setup") from exc
    return WalletSetupResponse(**result)


@app.post("/wallet/complete", response_model=WalletCompleteResponse)
async def wallet_complete(body: WalletCompleteRequest) -> WalletCompleteResponse:
    """Finalize card save after Stripe redirect."""
    if not stripe_wallet.is_configured():
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    try:
        done = stripe_wallet.complete_setup_session(body.session_id)
        has_card = stripe_wallet.customer_has_payment_method(done["stripe_customer_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("wallet complete failed")
        raise HTTPException(status_code=502, detail="Could not verify card setup") from exc

    await donor_db.upsert_profile(
        email=done["email"],
        stripe_customer_id=done["stripe_customer_id"],
        wallet_saved=has_card,
    )
    profile = await donor_db.profile_response(done["email"])
    return WalletCompleteResponse(
        email=profile["email"],
        has_saved_card=profile["has_saved_card"],
        display_name=profile.get("display_name"),
        wallet_saved_at=profile.get("wallet_saved_at"),
        link_ready=profile.get("link_ready", False),
    )


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
