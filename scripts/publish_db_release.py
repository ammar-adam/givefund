#!/usr/bin/env python3
"""Build db-manifest.json and print publish instructions for GitHub Releases."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    db_path = Path(os.getenv("DB_PATH", root / "givefund.db"))
    if not db_path.is_absolute():
        db_path = root / db_path

    if not db_path.exists():
        print(f"Missing database: {db_path}", file=sys.stderr)
        return 1

    data = db_path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    platforms = conn.execute(
        "SELECT platform, COUNT(*) FROM campaigns GROUP BY platform ORDER BY 2 DESC"
    ).fetchall()
    conn.close()

    manifest = {
        "campaign_count": count,
        "size_bytes": len(data),
        "sha256": sha,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "platforms": {p: n for p, n in platforms},
    }
    manifest_path = root / "db-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"\nWrote {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
