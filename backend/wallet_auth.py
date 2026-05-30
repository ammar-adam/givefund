"""Session token for wallet authentication.

Issues and verifies HMAC-SHA256 signed tokens after Google OAuth.
Tokens contain email + google_sub + expiry (7 days).

Environment:
    WALLET_SESSION_SECRET -- required; 32+ byte hex string.
                             Generate: openssl rand -hex 32
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)

TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _secret() -> bytes:
    raw = os.getenv("WALLET_SESSION_SECRET", "").strip()
    if not raw:
        raise RuntimeError(
            "WALLET_SESSION_SECRET is not set. "
            "Generate one with: openssl rand -hex 32"
        )
    return raw.encode()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_session_token(email: str, google_sub: str) -> str:
    """Create a signed session token for authenticated wallet operations."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "email": email.strip().lower(),
        "sub": google_sub,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = _b64url_encode(payload_json)
    sig = hmac.new(_secret(), payload_b64.encode(), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> dict[str, Any]:
    """Verify and decode a session token. Raises ValueError on failure."""
    if not token or "." not in token:
        raise ValueError("Malformed token")

    payload_b64, _, sig_b64 = token.partition(".")
    if not payload_b64 or not sig_b64:
        raise ValueError("Malformed token")

    expected_sig = hmac.new(_secret(), payload_b64.encode(), hashlib.sha256).digest()
    try:
        provided_sig = _b64url_decode(sig_b64)
    except Exception:
        raise ValueError("Malformed token signature")

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise ValueError("Malformed token payload")

    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise ValueError("Token expired")

    if not payload.get("email"):
        raise ValueError("Token missing email")

    return payload


async def require_wallet_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency -- validates Bearer token or raises 401."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Sign in with Google first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_session_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
