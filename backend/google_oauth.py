"""Verify Google Sign-In ID tokens for donor identity (optional)."""

from __future__ import annotations

import os


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID", "").strip())


def verify_credential(credential: str) -> dict[str, str]:
    """Return email, name, sub from Google ID token."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID not configured")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError as exc:
        raise RuntimeError("google-auth package required for Google sign-in") from exc

    idinfo = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )
    email = idinfo.get("email")
    if not email:
        raise ValueError("Google account has no email")
    return {
        "email": email.strip().lower(),
        "display_name": idinfo.get("name") or "",
        "google_sub": idinfo.get("sub") or "",
    }
