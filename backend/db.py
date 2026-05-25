import math
import os
from pathlib import Path
from typing import Any

import aiosqlite
from dotenv import load_dotenv

from models import Campaign


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_db_path() -> Path:
    """Return the configured SQLite database path."""

    configured_path = os.getenv("DB_PATH", "./givefund.db")
    path = Path(configured_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path.resolve()


async def connect_readonly() -> aiosqlite.Connection | None:
    """Open the campaign database in read-only mode if it exists."""

    db_path = get_db_path()
    if not db_path.exists():
        return None
    return await aiosqlite.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


async def _fetchone(
    connection: aiosqlite.Connection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> aiosqlite.Row | tuple[Any, ...] | None:
    """Execute a query and return one row."""

    async with connection.execute(sql, params or {}) as cursor:
        return await cursor.fetchone()


def _campaign_from_row(row: aiosqlite.Row) -> Campaign:
    """Convert a database row into the public campaign model."""

    goal_raw = row["goal_amount"]
    raised_raw = row["raised_amount"]
    goal_amount = float(goal_raw) if goal_raw is not None else 0.0
    raised_amount = float(raised_raw) if raised_raw is not None else 0.0
    funding_gap = (
        max(goal_amount - raised_amount, 0.0) if goal_raw is not None and raised_raw is not None else 0.0
    )
    if goal_raw is not None and raised_raw is not None and goal_amount > 0:
        pct_funded = round(min((raised_amount / goal_amount) * 100, 999.99), 2)
    else:
        pct_funded = 0.0

    keys = row.keys()
    location = row["location"] if "location" in keys else None

    return Campaign(
        id=row["id"],
        title=row["title"],
        story_snippet=row["story_snippet"],
        photo_url=row["photo_url"],
        goal_amount=goal_amount if row["goal_amount"] is not None else None,
        raised_amount=raised_amount if row["raised_amount"] is not None else None,
        funding_gap=funding_gap,
        pct_funded=pct_funded,
        platform=row["platform"] or "gofundme",
        campaign_url=row["campaign_url"],
        category=row["category"],
        location=location,
        scraped_at=row["scraped_at"],
    )


def _filters(
    search: str | None,
    category: str | None,
    platform: str | None,
) -> tuple[list[str], dict[str, Any]]:
    """Build reusable WHERE clauses and query parameters."""

    clauses: list[str] = []
    params: dict[str, Any] = {}

    if search:
        clauses.append("(LOWER(title) LIKE :search OR LOWER(story_snippet) LIKE :search)")
        params["search"] = f"%{search.lower()}%"

    if category:
        clauses.append("category = :category")
        params["category"] = category

    if platform:
        clauses.append("platform = :platform")
        params["platform"] = platform

    return clauses, params


def _where_sql(clauses: list[str]) -> str:
    """Return a WHERE clause for optional filters."""

    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


def _order_sql(sort_by: str) -> str:
    """Return the ORDER BY expression for a supported sort mode."""

    if sort_by == "almost_there":
        return """
        ORDER BY
          CASE WHEN goal_amount > 0 AND raised_amount >= goal_amount THEN 1 ELSE 0 END,
          CASE WHEN goal_amount > 0 THEN (raised_amount * 1.0 / goal_amount) ELSE 0 END DESC,
          scraped_at DESC
        """
    if sort_by == "newest":
        return "ORDER BY scraped_at DESC"
    return "ORDER BY (goal_amount - raised_amount) DESC, scraped_at DESC"


_SELECT_COLUMNS = """
    id, title, story_snippet, photo_url, goal_amount, raised_amount,
    platform, campaign_url, category, location, scraped_at
"""


async def get_campaigns(
    search: str | None,
    category: str | None,
    platform: str | None,
    sort_by: str,
    page: int,
    page_size: int,
) -> tuple[list[Campaign], int, int]:
    """Fetch filtered campaigns plus total count and page count."""

    connection = await connect_readonly()
    if connection is None:
        return [], 0, 0

    try:
        connection.row_factory = aiosqlite.Row
        clauses, params = _filters(search, category, platform)
        where_sql = _where_sql(clauses)
        offset = (page - 1) * page_size

        count_row = await _fetchone(
            connection,
            f"SELECT COUNT(*) AS total FROM campaigns {where_sql}",
            params,
        )
        total = int(count_row["total"] if count_row else 0)
        pages = math.ceil(total / page_size) if total else 0

        rows = await connection.execute_fetchall(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM campaigns
            {where_sql}
            {_order_sql(sort_by)}
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": page_size, "offset": offset},
        )
    finally:
        await connection.close()

    return [_campaign_from_row(row) for row in rows], total, pages


async def get_campaign(campaign_id: int) -> Campaign | None:
    """Fetch a single campaign by id."""

    connection = await connect_readonly()
    if connection is None:
        return None

    try:
        connection.row_factory = aiosqlite.Row
        row = await _fetchone(
            connection,
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM campaigns
            WHERE id = :campaign_id
            """,
            {"campaign_id": campaign_id},
        )
    finally:
        await connection.close()

    return _campaign_from_row(row) if row else None


async def get_categories() -> list[str]:
    """Fetch distinct campaign categories."""

    connection = await connect_readonly()
    if connection is None:
        return []

    try:
        rows = await connection.execute_fetchall(
            """
            SELECT DISTINCT category
            FROM campaigns
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
            """
        )
    finally:
        await connection.close()

    return [row[0] for row in rows]


async def get_platforms() -> list[str]:
    """Fetch distinct platforms present in the database."""

    connection = await connect_readonly()
    if connection is None:
        return []

    try:
        rows = await connection.execute_fetchall(
            """
            SELECT DISTINCT platform
            FROM campaigns
            WHERE platform IS NOT NULL AND platform != ''
            ORDER BY platform
            """
        )
    finally:
        await connection.close()

    return [row[0] for row in rows]


async def get_stats() -> dict[str, Any]:
    """Return aggregate stats for the stats endpoint."""

    connection = await connect_readonly()
    if connection is None:
        return {
            "total_campaigns": 0,
            "total_raised": 0.0,
            "platforms": [],
            "last_scraped": None,
        }

    try:
        connection.row_factory = aiosqlite.Row
        count_row = await _fetchone(
            connection,
            "SELECT COUNT(*) AS total_campaigns FROM campaigns",
        )
        row = await _fetchone(
            connection,
            """
            SELECT
              COALESCE(SUM(raised_amount), 0) AS total_raised,
              MAX(scraped_at) AS last_scraped
            FROM campaigns
            WHERE raised_amount IS NOT NULL AND raised_amount >= 0
            """,
        )
        platform_rows = await connection.execute_fetchall(
            """
            SELECT DISTINCT platform
            FROM campaigns
            WHERE platform IS NOT NULL
            ORDER BY platform
            """
        )
    finally:
        await connection.close()

    return {
        "total_campaigns": int(count_row["total_campaigns"] if count_row else 0),
        "total_raised": float(row["total_raised"] if row else 0),
        "platforms": [r[0] for r in platform_rows],
        "last_scraped": row["last_scraped"] if row else None,
    }


async def get_campaign_count() -> int:
    """Count available campaigns in the read-only database."""

    connection = await connect_readonly()
    if connection is None:
        return 0

    try:
        row = await _fetchone(connection, "SELECT COUNT(*) FROM campaigns")
    finally:
        await connection.close()

    return int(row[0] if row else 0)
