"""Donor wallet profiles (Stripe customer + saved email for checkout prefill)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiosqlite

from db import connect_readonly, get_db_path


async def _writable_connection() -> aiosqlite.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return await aiosqlite.connect(path)


async def ensure_donor_table(conn: aiosqlite.Connection) -> None:
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


async def get_profile(email: str) -> dict[str, Any] | None:
    email = email.strip().lower()
    conn = await connect_readonly()
    if conn is None:
        return None
    try:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM donor_profiles WHERE email = ?",
            (email,),
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        await conn.close()


async def upsert_profile(
    *,
    email: str,
    stripe_customer_id: str | None = None,
    display_name: str | None = None,
    google_sub: str | None = None,
    wallet_saved: bool = False,
) -> dict[str, Any]:
    email = email.strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    conn = await _writable_connection()
    try:
        await ensure_donor_table(conn)
        existing = await get_profile(email)
        saved_at = now if wallet_saved else (existing or {}).get("wallet_saved_at")
        await conn.execute(
            """
            INSERT INTO donor_profiles
                (email, stripe_customer_id, display_name, google_sub, wallet_saved_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                stripe_customer_id = COALESCE(excluded.stripe_customer_id, donor_profiles.stripe_customer_id),
                display_name = COALESCE(excluded.display_name, donor_profiles.display_name),
                google_sub = COALESCE(excluded.google_sub, donor_profiles.google_sub),
                wallet_saved_at = COALESCE(excluded.wallet_saved_at, donor_profiles.wallet_saved_at),
                updated_at = excluded.updated_at
            """,
            (
                email,
                stripe_customer_id,
                display_name,
                google_sub,
                saved_at,
                now,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()
    profile = await get_profile(email)
    return profile or {"email": email}


async def profile_response(email: str) -> dict[str, Any]:
    row = await get_profile(email.strip().lower())
    if not row:
        return {
            "email": email.strip().lower(),
            "has_saved_card": False,
            "display_name": None,
            "wallet_saved_at": None,
            "link_ready": False,
        }
    return {
        "email": row["email"],
        "has_saved_card": bool(row.get("stripe_customer_id") and row.get("wallet_saved_at")),
        "display_name": row.get("display_name"),
        "wallet_saved_at": row.get("wallet_saved_at"),
        "link_ready": bool(row.get("wallet_saved_at")),
    }
