"""Download givefund.db from DB_DOWNLOAD_URL before API startup (production sync)."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path


def _manifest_url(db_url: str) -> str:
    if db_url.endswith(".db"):
        return db_url.rsplit("/", 1)[0] + "/db-manifest.json"
    return db_url.replace("givefund.db", "db-manifest.json")


def _remote_manifest(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GiveFund-DB-Sync/1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print(f"Could not fetch manifest: {exc}")
        return None


def _local_count(db_path: Path) -> int:
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        n = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def main() -> int:
    if os.getenv("SKIP_DB_DOWNLOAD", "").lower() in ("1", "true", "yes"):
        print("SKIP_DB_DOWNLOAD set — skipping download")
        return 0

    url = os.getenv("DB_DOWNLOAD_URL", "").strip()
    if not url:
        return 0

    db_path = Path(os.getenv("DB_PATH", "./givefund.db"))
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[1] / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    force = os.getenv("FORCE_DB_DOWNLOAD", "").lower() in ("1", "true", "yes")

    manifest = _remote_manifest(_manifest_url(url))
    if manifest and not force:
        remote_count = int(manifest.get("campaign_count", 0))
        local_count = _local_count(db_path) if db_path.exists() else 0
        if local_count >= remote_count and remote_count > 0:
            print(
                f"Local DB already has {local_count} campaigns "
                f"(remote {remote_count}) — skip download"
            )
            return 0

    print(f"Downloading database from {url} -> {db_path}")
    tmp = db_path.with_suffix(".db.downloading")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GiveFund-DB-Sync/1"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = resp.read()
        tmp.write_bytes(data)
        tmp.replace(db_path)
        print(f"Downloaded {db_path.stat().st_size:,} bytes")
        if manifest:
            print(f"Remote manifest: {manifest.get('campaign_count', '?')} campaigns")
        print(f"Verified local count: {_local_count(db_path):,}")
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
