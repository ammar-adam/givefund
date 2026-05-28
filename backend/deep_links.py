"""Low-friction outbound checkout URLs — the shippable part of payment bypass research."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Stripe Link often appears on these hosts' checkouts (donor still on their site).
LINK_LIKELY_PLATFORMS = frozenset(
    {"givebutter", "donorbox", "fundly", "globalgiving", "mightycause"}
)

# Query param name for donor email where we've seen or documented support.
EMAIL_QUERY_PARAMS: dict[str, str] = {
    "givebutter": "email",
    "donorbox": "email",
    "mightycause": "email",
    "globalgiving": "email",
}

PLATFORM_CHECKOUT_NOTES: dict[str, str] = {
    "gofundme": "Opens GoFundMe donate. Link may appear if they use Stripe for your region — use the same email you saved on GiveFund.",
    "launchgood": "Opens LaunchGood checkout. Card is entered on LaunchGood (Link usually not available).",
    "givebutter": "Givebutter uses Stripe — Link often works with the same email.",
    "donorbox": "Donorbox + Stripe — Link is commonly available on OmniGive forms.",
    "fundly": "SignUpGenius Donations (Stripe) — Link may autofill with the same email.",
    "globalgiving": "GlobalGiving checkout — email prefill when supported.",
}


def _slug_from_gofundme(url: str) -> str | None:
    parts = urlparse(url).path.strip("/").split("/")
    if "f" in parts:
        idx = parts.index("f")
        if idx + 1 < len(parts):
            slug = parts[idx + 1].split("?")[0]
            return slug if slug and slug != "donate" else None
    return None


def _slug_from_launchgood(url: str) -> str | None:
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "v4" and parts[1] == "campaign":
        return parts[2].split("?")[0] or None
    if parts and parts[0] == "project" and len(parts) > 1:
        return parts[1].split("?")[0] or None
    if "campaign" in parts:
        idx = parts.index("campaign")
        if idx + 1 < len(parts):
            return parts[idx + 1].split("?")[0] or None
    return None


def build_donate_url(
    *,
    platform: str,
    campaign_url: str,
    campaign_id: int | None = None,
    donor_email: str | None = None,
) -> str:
    """Best public donate URL + UTMs + email prefill when the platform supports it."""
    platform = (platform or "unknown").lower()
    fallback = (campaign_url or "").strip()
    if not fallback:
        return "#"

    target = fallback
    if platform == "gofundme":
        slug = _slug_from_gofundme(fallback)
        if slug:
            target = f"https://www.gofundme.com/f/{slug}/donate"
    elif platform == "launchgood":
        slug = _slug_from_launchgood(fallback)
        if slug:
            target = f"https://www.launchgood.com/v4/campaign/{slug}/donate"

    parsed = urlparse(target)
    query = parse_qs(parsed.query, keep_blank_values=True)
    flat = {k: v[0] for k, v in query.items() if v}

    flat.setdefault("utm_source", "givefund")
    flat.setdefault("utm_medium", "referral")
    flat.setdefault("utm_campaign", platform)
    if campaign_id is not None:
        flat.setdefault("utm_content", str(campaign_id))

    email_key = EMAIL_QUERY_PARAMS.get(platform)
    if donor_email and email_key:
        flat[email_key] = donor_email.strip()

    new_query = urlencode(flat)
    return urlunparse(parsed._replace(query=new_query))


def checkout_assist(
    *,
    platform: str,
    campaign_url: str,
    campaign_id: int,
    title: str | None,
    donor_email: str | None = None,
) -> dict:
    """Payload for Express Give UI."""
    platform = (platform or "unknown").lower()
    donate_url = build_donate_url(
        platform=platform,
        campaign_url=campaign_url,
        campaign_id=campaign_id,
        donor_email=donor_email,
    )
    return {
        "campaign_id": campaign_id,
        "title": title,
        "platform": platform,
        "donate_url": donate_url,
        "link_likely": platform in LINK_LIKELY_PLATFORMS,
        "email_prefill_supported": platform in EMAIL_QUERY_PARAMS,
        "checkout_note": PLATFORM_CHECKOUT_NOTES.get(
            platform,
            "You complete payment on the original platform. GiveFund never holds funds.",
        ),
        "steps_saved_estimate": (
            "Often skips card typing on Link-enabled checkouts (same email)."
            if platform in LINK_LIKELY_PLATFORMS
            else "Skips the story page — you land on checkout directly."
        ),
        "cannot_token_charge": True,
        "cannot_token_charge_reason": (
            "Platforms do not accept payment tokens from third parties. "
            "GiveFund can only open the official checkout and prefill where allowed."
        ),
    }
