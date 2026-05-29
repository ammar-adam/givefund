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
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS donor_profiles (
            email TEXT PRIMARY KEY,
            stripe_customer_id TEXT,
            display_name TEXT,
            google_sub TEXT,
            wallet_saved_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.commit()


_UPSERT_SQL = """
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
"""


def _campaign_params(campaign: dict) -> dict:
    return {
        "title": campaign.get("title"),
        "story_snippet": campaign.get("story_snippet"),
        "photo_url": campaign.get("photo_url"),
        "goal_amount": campaign.get("goal_amount"),
        "raised_amount": campaign.get("raised_amount"),
        "platform": campaign.get("platform", "gofundme"),
        "campaign_url": campaign.get("campaign_url"),
        "category": campaign.get("category"),
        "location": campaign.get("location"),
    }


async def upsert_campaign(conn: aiosqlite.Connection, campaign: dict) -> None:
    """Insert or update a campaign row, keyed on campaign_url."""
    await conn.execute(_UPSERT_SQL, _campaign_params(campaign))
    await conn.commit()


async def persist_campaigns_batch(
    conn: aiosqlite.Connection, campaigns: list[dict]
) -> int:
    """Upsert many campaigns in one transaction (live ingest)."""

    saved = 0
    for campaign in campaigns:
        if not campaign.get("campaign_url"):
            continue
        try:
            await conn.execute(_UPSERT_SQL, _campaign_params(campaign))
            saved += 1
        except Exception:
            continue
    await conn.commit()
    return saved


async def ensure_ingest_tables(conn: aiosqlite.Connection) -> None:
    """Tables for live scrape run tracking."""

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ingest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME,
            status TEXT DEFAULT 'running',
            total_scraped INTEGER DEFAULT 0,
            total_saved INTEGER DEFAULT 0,
            notes TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ingest_platform_stats (
            run_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            scraped INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0,
            db_total INTEGER DEFAULT 0,
            duration_sec REAL DEFAULT 0,
            error TEXT,
            PRIMARY KEY (run_id, platform)
        )
    """)
    await conn.commit()


async def start_ingest_run(conn: aiosqlite.Connection) -> int:
    await ensure_ingest_tables(conn)
    cursor = await conn.execute(
        "INSERT INTO ingest_runs (status) VALUES ('running')"
    )
    await conn.commit()
    return int(cursor.lastrowid)


async def finish_ingest_run(
    conn: aiosqlite.Connection,
    run_id: int,
    *,
    total_scraped: int,
    total_saved: int,
    status: str = "ok",
    notes: str | None = None,
) -> None:
    await conn.execute(
        """
        UPDATE ingest_runs
        SET finished_at = CURRENT_TIMESTAMP,
            status = ?,
            total_scraped = ?,
            total_saved = ?,
            notes = ?
        WHERE id = ?
        """,
        (status, total_scraped, total_saved, notes, run_id),
    )
    await conn.commit()


async def record_platform_stat(
    conn: aiosqlite.Connection,
    run_id: int,
    platform: str,
    scraped: int,
    saved: int,
    db_total: int,
    duration_sec: float,
    error: str | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO ingest_platform_stats
            (run_id, platform, scraped, saved, db_total, duration_sec, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, platform) DO UPDATE SET
            scraped = excluded.scraped,
            saved = excluded.saved,
            db_total = excluded.db_total,
            duration_sec = excluded.duration_sec,
            error = excluded.error
        """,
        (run_id, platform, scraped, saved, db_total, duration_sec, error),
    )
    await conn.commit()


async def get_latest_ingest_summary(conn: aiosqlite.Connection) -> dict | None:
    await ensure_ingest_tables(conn)
    cursor = await conn.execute(
        """
        SELECT id, started_at, finished_at, status, total_scraped, total_saved, notes
        FROM ingest_runs
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = await cursor.fetchone()
    if not row:
        return None
    run_id = row[0]
    pcursor = await conn.execute(
        """
        SELECT platform, scraped, saved, db_total, duration_sec, error
        FROM ingest_platform_stats
        WHERE run_id = ?
        ORDER BY db_total DESC
        """,
        (run_id,),
    )
    platforms = [
        {
            "platform": r[0],
            "scraped": r[1],
            "saved": r[2],
            "db_total": r[3],
            "duration_sec": r[4],
            "error": r[5],
        }
        for r in await pcursor.fetchall()
    ]
    return {
        "run_id": run_id,
        "started_at": row[1],
        "finished_at": row[2],
        "status": row[3],
        "total_scraped": row[4],
        "total_saved": row[5],
        "notes": row[6],
        "platforms": platforms,
    }


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
