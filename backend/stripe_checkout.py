"""Stripe Checkout sessions for Link enrollment (optional GiveFund tip)."""

from __future__ import annotations

import os

import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

MIN_TIP_CENTS = 100
MAX_TIP_CENTS = 50_000
DEFAULT_TIP_CENTS = 500


def is_configured() -> bool:
    """True when STRIPE_SECRET_KEY is set."""

    return bool(stripe.api_key)


def get_publishable_key() -> str | None:
    """Return Stripe publishable key for frontend, if configured."""

    key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    return key or None


def create_link_setup_session(
    *,
    email: str,
    amount_cents: int,
    success_url: str,
    cancel_url: str,
    campaign_id: int | None = None,
) -> dict[str, str]:
    """
    Create a one-time Checkout Session so the donor enrolls in Stripe Link.

    Campaign donations still happen on the original platform; this is a
    small optional tip to GiveFund that seeds Link for faster checkout elsewhere.
    """

    if not is_configured():
        raise RuntimeError("Stripe is not configured")

    amount = max(MIN_TIP_CENTS, min(amount_cents, MAX_TIP_CENTS))
    metadata: dict[str, str] = {
        "purpose": "link_enrollment",
        "product": "givefund_tip",
    }
    if campaign_id is not None:
        metadata["campaign_id"] = str(campaign_id)

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=email.strip().lower(),
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount,
                    "product_data": {
                        "name": "Support GiveFund",
                        "description": (
                            "Optional tip to keep discovery free. "
                            "Checkout also saves your card with Stripe Link "
                            "for faster giving on participating sites."
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        payment_method_types=["card"],
    )
    if not session.url:
        raise RuntimeError("Stripe did not return a checkout URL")
    return {"session_id": session.id, "url": session.url}
