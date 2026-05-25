"""Database helpers for the scraper -- writes to givefund.db."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DB_PATH: str = os.getenv("DB_PATH", "./givefund.db")
if not Path(DB_PATH).is_absolute():
    DB_PATH = str((Path(__file__).resolve().parents[1] / DB_PATH).resolve())


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Yield an aiosqlite connection, closing it on exit."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def create_table(conn: aiosqlite.Connection) -> None:
    """Create the campaigns table and indexes if they do not exist."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            story_snippet TEXT,
            photo_url TEXT,
            goal_amount REAL,
            raised_amount REAL,
            platform TEXT DEFAULT 'gofundme',
            campaign_url TEXT UNIQUE,
            category TEXT,
            location TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_platform ON campaigns(platform)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_category ON campaigns(category)"
    )
    # Migrate older DBs missing location column
    cursor = await conn.execute("PRAGMA table_info(campaigns)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "location" not in columns:
        await conn.execute("ALTER TABLE campaigns ADD COLUMN location TEXT")
    await conn.commit()


async def upsert_campaign(conn: aiosqlite.Connection, campaign: dict) -> None:
    """Insert or update a campaign row, keyed on campaign_url."""
    await conn.execute("""
        INSERT INTO campaigns
            (title, story_snippet, photo_url, goal_amount, raised_amount,
             platform, campaign_url, category, location)
        VALUES
            (:title, :story_snippet, :photo_url, :goal_amount, :raised_amount,
             :platform, :campaign_url, :category, :location)
        ON CONFLICT(campaign_url) DO UPDATE SET
            title          = excluded.title,
            story_snippet  = excluded.story_snippet,
            photo_url      = excluded.photo_url,
            goal_amount    = excluded.goal_amount,
            raised_amount  = excluded.raised_amount,
            platform       = excluded.platform,
            category       = excluded.category,
            location       = excluded.location,
            scraped_at     = CURRENT_TIMESTAMP
    """, {
        "title": campaign.get("title"),
        "story_snippet": campaign.get("story_snippet"),
        "photo_url": campaign.get("photo_url"),
        "goal_amount": campaign.get("goal_amount"),
        "raised_amount": campaign.get("raised_amount"),
        "platform": campaign.get("platform", "gofundme"),
        "campaign_url": campaign.get("campaign_url"),
        "category": campaign.get("category"),
        "location": campaign.get("location"),
    })
    await conn.commit()


async def count_campaigns(conn: aiosqlite.Connection, platform: str | None = None) -> int:
    """Return row count, optionally filtered by platform."""
    if platform:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM campaigns WHERE platform = ?",
            (platform,),
        )
    else:
        cursor = await conn.execute("SELECT COUNT(*) FROM campaigns")
    row = await cursor.fetchone()
    return int(row[0]) if row else 0
