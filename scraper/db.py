"""Database helpers for the scraper -- writes to givefund.db."""

import os
from typing import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DB_PATH: str = os.getenv("DB_PATH", "./givefund.db")


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
    """Create the campaigns table if it does not already exist."""
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
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.commit()


async def upsert_campaign(conn: aiosqlite.Connection, campaign: dict) -> None:
    """Insert or update a campaign row, keyed on campaign_url."""
    await conn.execute("""
        INSERT INTO campaigns
            (title, story_snippet, photo_url, goal_amount, raised_amount,
             platform, campaign_url, category)
        VALUES
            (:title, :story_snippet, :photo_url, :goal_amount, :raised_amount,
             :platform, :campaign_url, :category)
        ON CONFLICT(campaign_url) DO UPDATE SET
            title          = excluded.title,
            story_snippet  = excluded.story_snippet,
            photo_url      = excluded.photo_url,
            goal_amount    = excluded.goal_amount,
            raised_amount  = excluded.raised_amount,
            scraped_at     = CURRENT_TIMESTAMP
    """, campaign)
    await conn.commit()
