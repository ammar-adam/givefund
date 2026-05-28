"""Save donor cards via Stripe Checkout (setup mode) — no charge, enrolls Stripe Link."""

from __future__ import annotations

import os

import stripe

DEFAULT_SUCCESS = "http://127.0.0.1:5500/wallet-success.html"


def is_configured() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY", "").strip())


def get_publishable_key() -> str | None:
    key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    return key or None


def create_setup_session(
    *,
    email: str,
    success_url: str,
    cancel_url: str,
) -> dict[str, str]:
    """Stripe Checkout in setup mode — saves payment method to customer (Link eligible)."""
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")

    stripe.api_key = secret
    session = stripe.checkout.Session.create(
        mode="setup",
        customer_email=email.strip(),
        payment_method_types=["card"],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"session_id": session.id, "url": session.url}
