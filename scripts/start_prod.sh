#!/usr/bin/env bash
# Production start: sync DB, optional live scraper daemon, API.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DB_PATH="${DB_PATH:-/var/data/givefund.db}"
python scripts/download_db.py || true
export LIVE_SCRAPE="${LIVE_SCRAPE:-true}"
export SCRAPE_INTERVAL="${SCRAPE_INTERVAL:-1800}"
export SCRAPE_ON_START="${SCRAPE_ON_START:-true}"
MIN_CAMPAIGNS="${MIN_CAMPAIGNS:-10000}"

COUNT=$(python -c "import sqlite3, os, pathlib
p = os.environ['DB_PATH']
print(0 if not pathlib.Path(p).exists() else sqlite3.connect(p).execute('SELECT COUNT(*) FROM campaigns').fetchone()[0])" 2>/dev/null || echo 0)

if [ "$COUNT" -lt "$MIN_CAMPAIGNS" ]; then
  echo "Database has $COUNT campaigns (min $MIN_CAMPAIGNS) — running scale ingest..."
  cd scraper
  pip install -r requirements.txt -q 2>/dev/null || true
  playwright install chromium 2>/dev/null || true
  export GFM_ALGOLIA_ONLY=true
  export GFM_MAX_ALGOLIA_PAGES="${GFM_MAX_ALGOLIA_PAGES:-100}"
  python scale_ingest.py --target "${SCALE_TARGET:-10000}" --parallel "${SCRAPE_PARALLEL:-4}" || true
  cd "$ROOT"
fi

if [ "$LIVE_SCRAPE" = "true" ]; then
  echo "Starting background live scraper (every ${SCRAPE_INTERVAL}s)..."
  (
    cd "$ROOT/scraper"
    while true; do
      python live_runner.py --once --parallel "${SCRAPE_PARALLEL:-4}" || true
      sleep "$SCRAPE_INTERVAL"
    done
  ) >> "${LIVE_SCRAPE_LOG:-/tmp/givefund-scrape.log}" 2>&1 &
fi

cd backend
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
