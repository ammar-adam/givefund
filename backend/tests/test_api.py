"""API contract smoke tests against a temporary SQLite database."""

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DB_PATH"] = str(Path(__file__).resolve().parents[2] / "givefund-test.db")

import db  # noqa: E402
from main import app  # noqa: E402

DB_FILE = Path(os.environ["DB_PATH"])


@pytest.fixture(autouse=True)
def fresh_db():
    """Create a clean database with one sample campaign per test."""
    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            story_snippet TEXT,
            photo_url TEXT,
            goal_amount REAL,
            raised_amount REAL,
            platform TEXT,
            campaign_url TEXT UNIQUE,
            category TEXT,
            location TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        """
        INSERT INTO campaigns
          (title, story_snippet, photo_url, goal_amount, raised_amount,
           platform, campaign_url, category, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Help Maria",
            "Medical fundraiser for Maria",
            "https://example.com/img.jpg",
            10000.0,
            2500.0,
            "gofundme",
            "https://www.gofundme.com/f/test-maria",
            "medical",
            "Chicago, IL",
        ),
    )
    conn.commit()
    conn.close()
    yield
    if DB_FILE.exists():
        DB_FILE.unlink()


@pytest.fixture
def client():
    """HTTP client for the FastAPI app."""
    return TestClient(app)


def test_health(client):
    """Health endpoint returns ok and a positive campaign count."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["campaign_count"] == 1


def test_campaigns_shape(client):
    """List endpoint returns computed funding fields."""
    response = client.get("/campaigns")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    campaign = payload["campaigns"][0]
    assert campaign["funding_gap"] == 7500.0
    assert campaign["pct_funded"] == 25.0
    assert campaign["platform"] == "gofundme"
    assert campaign["location"] == "Chicago, IL"


def test_campaigns_search(client):
    """Search filter matches title and story."""
    response = client.get("/campaigns", params={"search": "maria"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    empty = client.get("/campaigns", params={"search": "zzznomatch"})
    assert empty.json()["total"] == 0


def test_platform_catalog(client):
    catalog = client.get("/platforms/catalog").json()
    assert catalog["count"] >= 10
    ids = {p["id"] for p in catalog["platforms"]}
    assert "gofundme" in ids
    assert "justgiving" in ids


def test_checkout_assist(client):
    """Express Give checkout assist returns donate URL."""
    response = client.get("/campaigns/1/checkout?email=donor@example.com")
    assert response.status_code == 200
    data = response.json()
    assert "donate_url" in data
    assert data["campaign_id"] == 1
    assert "gofundme" in data["donate_url"] or data["platform"] == "gofundme"
    assert data["cannot_token_charge"] is True


def test_search_live_validation(client):
    """Live search requires at least 2 characters."""
    assert client.get("/search/live?q=a").status_code == 422


def test_ingest_status(client):
    """Ingest status endpoint returns live tracking shape."""
    response = client.get("/ingest/status")
    assert response.status_code == 200
    data = response.json()
    assert data["live_tracking"] is True
    assert "total_campaigns" in data
    assert "refresh_interval_sec" in data


def test_platforms_and_stats(client):
    """Aggregate endpoints return expected keys."""
    platforms = client.get("/platforms").json()
    assert "gofundme" in platforms["platforms"]

    stats = client.get("/stats").json()
    assert stats["total_campaigns"] == 1
    assert stats["total_raised"] == 2500.0


def test_campaign_not_found(client):
    """Missing id returns 404."""
    response = client.get("/campaigns/9999")
    assert response.status_code == 404


def test_invalid_page_returns_422(client):
    """Invalid query params return 422 with a message."""
    response = client.get("/campaigns", params={"page": 0})
    assert response.status_code == 422
    assert "detail" in response.json()

