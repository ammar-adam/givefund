"""Download givefund.db from a URL before API startup (prod sync)."""

import os
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    """Download DB file when DB_DOWNLOAD_URL is set."""
    url = os.getenv("DB_DOWNLOAD_URL", "").strip()
    if not url:
        return 0

    db_path = Path(os.getenv("DB_PATH", "./givefund.db"))
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[1] / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading database from {url} -> {db_path}")
    urllib.request.urlretrieve(url, db_path)
    print(f"Downloaded {db_path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
