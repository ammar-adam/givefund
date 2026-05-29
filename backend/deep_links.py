"""Low-friction outbound checkout URLs — deep links + donor prefill."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

LINK_LIKELY_PLATFORMS = frozenset(
    {
        "givebutter",
        "donorbox",
        "fundly",
        "globalgiving",
        "mightycause",
        "givesendgo",
        "whydonate",
        "impactguru",
    }
)

# Query keys per platform for donor prefill (email / name where supported).
EMAIL_QUERY_PARAMS: dict[str, str] = {
    "givebutter": "email",
    "donorbox": "email",
    "mightycause": "email",
    "globalgiving": "email",
    "justgiving": "email",
    "whydonate": "email",
    "impactguru": "email",
    "ketto": "email",
    "milaap": "email",
    "givesendgo": "email",
    "givengain": "email",
    "chuffed": "email",
    "fundrazr": "email",
    "gogetfunding": "email",
}

NAME_QUERY_PARAMS: dict[str, tuple[str, str]] = {
    "donorbox": ("first_name", "last_name"),
    "givebutter": ("fname", "lname"),
    "globalgiving": ("first_name", "last_name"),
}

PLATFORM_CHECKOUT_NOTES: dict[str, str] = {
    "gofundme": "Opens GoFundMe /donate. Use the same email you saved on GiveFund — Link may appear if they use Stripe.",
    "launchgood": "LaunchGood checkout. Card entry on their site (Link usually not available).",
    "givebutter": "Stripe checkout — Link often autofills with your saved email.",
    "donorbox": "Donorbox + Stripe — Link common on OmniGive forms.",
    "fundly": "SignUpGenius Donations (Stripe) — Link may work with same email.",
    "globalgiving": "GlobalGiving — email and name prefilled when supported.",
    "givesendgo": "GiveSendGo — email prefill on donate flow when supported.",
    "whydonate": "WhyDonate EU — email in URL when supported.",
    "impactguru": "ImpactGuru India — search and donate with email hint.",
    "ketto": "Ketto — complete payment on ketto.org.",
    "milaap": "Milaap — complete payment on milaap.org.",
    "givengain": "GivenGain — international charity crowdfunding.",
    "leetchi": "Leetchi / Lydia — EU collective pots.",
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


def _split_name(display_name: str | None) -> tuple[str | None, str | None]:
    if not display_name or not display_name.strip():
        return None, None
    parts = display_name.strip().split(None, 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else None
    return first, last


def build_donate_url(
    *,
    platform: str,
    campaign_url: str,
    campaign_id: int | None = None,
    donor_email: str | None = None,
    donor_name: str | None = None,
) -> str:
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

    first, last = _split_name(donor_name)
    name_keys = NAME_QUERY_PARAMS.get(platform)
    if name_keys and first:
        flat[name_keys[0]] = first
        if last:
            flat[name_keys[1]] = last

    return urlunparse(parsed._replace(query=urlencode(flat)))


def checkout_assist(
    *,
    platform: str,
    campaign_url: str,
    campaign_id: int,
    title: str | None,
    donor_email: str | None = None,
    donor_name: str | None = None,
    wallet_saved: bool = False,
) -> dict:
    platform = (platform or "unknown").lower()
    donate_url = build_donate_url(
        platform=platform,
        campaign_url=campaign_url,
        campaign_id=campaign_id,
        donor_email=donor_email,
        donor_name=donor_name,
    )
    prefill: list[str] = []
    if donor_email and platform in EMAIL_QUERY_PARAMS:
        prefill.append("email")
    if donor_name and platform in NAME_QUERY_PARAMS:
        prefill.append("name")

    return {
        "campaign_id": campaign_id,
        "title": title,
        "platform": platform,
        "donate_url": donate_url,
        "link_likely": platform in LINK_LIKELY_PLATFORMS or wallet_saved,
        "email_prefill_supported": platform in EMAIL_QUERY_PARAMS,
        "prefill_fields": prefill,
        "donor_email": donor_email,
        "donor_name": donor_name,
        "wallet_saved": wallet_saved,
        "checkout_note": PLATFORM_CHECKOUT_NOTES.get(
            platform,
            "Complete payment on the original platform. GiveFund never holds funds.",
        ),
        "steps_saved_estimate": (
            "Saved card + same email → Stripe Link may skip card entry on this site."
            if wallet_saved and platform in LINK_LIKELY_PLATFORMS
            else "Deep link to checkout — fewer clicks than the story page."
        ),
        "cannot_token_charge": True,
        "cannot_token_charge_reason": (
            "Platforms do not accept GiveFund payment tokens. We prefill allowed fields "
            "and Stripe Link may autofill on their checkout when they use Stripe."
        ),
    }
