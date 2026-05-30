"""Redirect URL validation to prevent open-redirect attacks.

Ensures any client-supplied URL stays within the configured frontend origin.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import HTTPException


def _frontend_origin() -> str:
    base = os.getenv("GIVEFUND_FRONTEND_URL", "http://127.0.0.1:5500").rstrip("/")
    parsed = urlparse(base)
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_redirect_url(url: str, *, allowed_base: str | None = None) -> str:
    """Validate that url is under the allowed frontend origin.

    Returns the validated url on success.
    Raises HTTPException(400) on rejection.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Redirect URL must not be empty")

    origin = allowed_base or _frontend_origin()
    parsed = urlparse(url)
    url_origin = f"{parsed.scheme}://{parsed.netloc}"

    # Allow localhost / 127.0.0.1 in development
    dev_origins = {
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }

    if url_origin != origin and url_origin not in dev_origins:
        raise HTTPException(
            status_code=400,
            detail=f"Redirect URL not allowed. Must be under {origin}.",
        )
    return url
