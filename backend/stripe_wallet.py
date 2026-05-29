"""Stripe Customer + Checkout setup — saves card and enrolls Stripe Link (payment OAuth)."""

from __future__ import annotations

import os
from typing import Any

import stripe


def is_configured() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY", "").strip())


def get_publishable_key() -> str | None:
    key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    return key or None


def _stripe() -> None:
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")
    stripe.api_key = secret


def get_or_create_customer(email: str, *, name: str | None = None) -> dict[str, Any]:
    """Find or create Stripe Customer for this donor email."""
    _stripe()
    email = email.strip().lower()
    existing = stripe.Customer.list(email=email, limit=1)
    if existing.data:
        customer = existing.data[0]
        if name and not customer.name:
            customer = stripe.Customer.modify(customer.id, name=name)
        return customer

    params: dict[str, Any] = {"email": email}
    if name:
        params["name"] = name
    return stripe.Customer.create(**params)


def create_setup_session(
    *,
    email: str,
    success_url: str,
    cancel_url: str,
    display_name: str | None = None,
) -> dict[str, str]:
    """
    Checkout in setup mode — saves payment method on Customer.
    Enables Stripe Link for cross-merchant autofill (same email on other sites).
    """
    customer = get_or_create_customer(email, name=display_name)
    sep = "&" if "?" in success_url else "?"
    success_with_session = f"{success_url}{sep}session_id={{CHECKOUT_SESSION_ID}}"

    session = stripe.checkout.Session.create(
        mode="setup",
        customer=customer.id,
        payment_method_types=["card"],
        success_url=success_with_session,
        cancel_url=cancel_url,
        metadata={"givefund_email": email.strip().lower()},
    )
    return {
        "session_id": session.id,
        "url": session.url,
        "stripe_customer_id": customer.id,
    }


def complete_setup_session(session_id: str) -> dict[str, Any]:
    """Verify checkout session completed and return customer + email."""
    _stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    if session.status != "complete":
        raise ValueError(f"Checkout session not complete: {session.status}")
    email = (session.metadata or {}).get("givefund_email") or session.customer_details.email
    if not email and session.customer:
        customer = stripe.Customer.retrieve(session.customer)
        email = customer.email
    if not email:
        raise ValueError("No email on completed session")
    return {
        "email": email.strip().lower(),
        "stripe_customer_id": str(session.customer),
        "session_id": session.id,
    }


def customer_has_payment_method(customer_id: str) -> bool:
    _stripe()
    methods = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=1)
    return len(methods.data) > 0
