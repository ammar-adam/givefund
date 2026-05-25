#!/usr/bin/env bash
# Production start: sync DB, run scraper if sparse, start API.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python scripts/download_db.py || true

export DB_PATH="${DB_PATH:-$ROOT/givefund.db}"
export SCRAPE_ON_START="${SCRAPE_ON_START:-true}"
MIN_CAMPAIGNS="${MIN_CAMPAIGNS:-50}"

COUNT=$(python -c "import sqlite3, os, pathlib
p = os.environ['DB_PATH']
print(0 if not pathlib.Path(p).exists() else sqlite3.connect(p).execute('SELECT COUNT(*) FROM campaigns').fetchone()[0])" 2>/dev/null || echo 0)

if [ "$SCRAPE_ON_START" = "true" ] && [ "$COUNT" -lt "$MIN_CAMPAIGNS" ]; then
  echo "Database has $COUNT campaigns (min $MIN_CAMPAIGNS) — running scraper..."
  cd scraper
  pip install -r requirements.txt -q
  playwright install chromium 2>/dev/null || true
  python main.py --platform gofundme || true
  python main.py --platform launchgood || true
  cd "$ROOT"
fi

cd backend
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
