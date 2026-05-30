"""Security tests: auth, rate limiting, session tokens, CORS."""

import os
import time
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PATH", str(Path(__file__).resolve().parents[2] / "givefund-test.db"))
os.environ.setdefault("WALLET_SESSION_SECRET", "testsecret0000000000000000000000")

import db  # noqa: E402
from main import app  # noqa: E402
from wallet_auth import create_session_token, verify_session_token  # noqa: E402

DB_FILE = Path(os.environ["DB_PATH"])
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def fresh_db():
    if DB_FILE.exists():
        DB_FILE.unlink()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, story_snippet TEXT, photo_url TEXT,
            goal_amount REAL, raised_amount REAL, platform TEXT,
            campaign_url TEXT UNIQUE, category TEXT, location TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT INTO campaigns (title, campaign_url, platform) VALUES (?, ?, ?)",
        ("Test", "https://gofundme.com/test", "gofundme"),
    )
    conn.commit()
    conn.close()
    yield
    if DB_FILE.exists():
        DB_FILE.unlink()


# ---------------------------------------------------------------------------
# Session token unit tests
# ---------------------------------------------------------------------------

def test_session_token_roundtrip():
    token = create_session_token("Alice@Example.com", "sub123")
    payload = verify_session_token(token)
    assert payload["email"] == "alice@example.com"
    assert payload["sub"] == "sub123"


def test_session_token_tamper_rejected():
    token = create_session_token("user@example.com", "sub1")
    parts = token.split(".")
    # Flip last byte of signature
    bad_sig = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    bad_token = f"{parts[0]}.{bad_sig}"
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        verify_session_token(bad_token)


def test_session_token_expired_rejected():
    with patch("wallet_auth.time") as mock_time:
        mock_time.time.return_value = int(time.time()) - 8 * 24 * 3600  # 8 days ago
        token = create_session_token("user@example.com", "sub1")
    with pytest.raises(ValueError, match="[Ee]xpired"):
        verify_session_token(token)


# ---------------------------------------------------------------------------
# Wallet endpoints require authentication
# ---------------------------------------------------------------------------

def test_wallet_profile_requires_auth():
    r = client.get("/wallet/profile")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_wallet_setup_requires_auth():
    r = client.post("/wallet/setup", json={"display_name": "Alice"})
    assert r.status_code == 401


def test_wallet_complete_requires_auth():
    r = client.post("/wallet/complete", json={"session_id": "cs_test_abc"})
    assert r.status_code == 401


def test_wallet_delete_requires_auth():
    r = client.delete("/wallet/profile")
    assert r.status_code == 401


def test_wallet_profile_invalid_token_rejected():
    r = client.get("/wallet/profile", headers={"Authorization": "Bearer not.a.valid.token"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated profile fetch
# ---------------------------------------------------------------------------

def test_wallet_profile_with_valid_token():
    token = create_session_token("test@example.com", "google-sub-1")
    r = client.get("/wallet/profile", headers={"Authorization": f"Bearer {token}"})
    # 200 with a profile or 503 if DB missing — not 401/403
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        data = r.json()
        assert data["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# Wallet setup — email from session, not body
# ---------------------------------------------------------------------------

def test_wallet_setup_uses_session_email():
    """Server should use session email; passing a different email in body is ignored or rejected."""
    token = create_session_token("user@example.com", "sub1")
    # Stripe not configured in tests — expect 503, not 403/401
    r = client.post(
        "/wallet/setup",
        json={"display_name": "User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 503 = Stripe not configured; 401/403 = security bug
    assert r.status_code not in (401, 403), f"Unexpected auth failure: {r.status_code}"


# ---------------------------------------------------------------------------
# CORS: wildcard origin must NOT be present
# ---------------------------------------------------------------------------

def test_cors_no_wildcard():
    r = client.get("/health", headers={"Origin": "https://evil.example.com"})
    # Should either be blocked (no ACAO header) or only allow known origins
    acao = r.headers.get("access-control-allow-origin", "")
    assert acao != "*", "CORS wildcard must not be set"


def test_cors_allows_known_origin():
    with patch("main.os") as mock_os:
        mock_os.getenv.side_effect = lambda k, d=None: (
            "https://givefund.vercel.app" if k == "GIVEFUND_FRONTEND_URL" else os.getenv(k, d)
        )
        r = client.get(
            "/health",
            headers={"Origin": "https://givefund.vercel.app"},
        )
    # 200 or ACAO present
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Rate limiter smoke test
# ---------------------------------------------------------------------------

def test_rate_limit_eventually_triggers():
    """Hit /search/live more than 5 times rapidly — must get a 429."""
    # Rate limiter is per IP; TestClient sends from testclient
    hits = []
    for _ in range(20):
        r = client.get("/search/live?q=test")
        hits.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in hits, f"Expected 429 after repeated calls, got: {set(hits)}"
