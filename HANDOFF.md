# GiveFund — Handoff

## What this is

GiveFund aggregates crowdfunding campaigns from GoFundMe, LaunchGood, and Fundly into one searchable site. The scraper writes SQLite; the backend serves REST; the frontend is a single HTML file.

## Prerequisites

- Python 3.11+ (3.11 recommended; 3.13 may need MSVC build tools for Playwright)
- Root `.env` (copy from `.env.example`):

```
DB_PATH=./givefund.db
PORT=8000
```

## 1. Scraper

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
```

**Seed sample data** (fast, no browser):

```bash
python seed_db.py
```

**Scrape one platform:**

```bash
python main.py --platform gofundme
python main.py --platform gofundme --category medical
python main.py --platform all
```

**Daily scheduler** (runs all platforms every 24h):

```bash
python scheduler.py
```

Writes to `givefund.db` at repo root (path from `DB_PATH`).

## 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

From repo root with `.env` loaded automatically.

**Smoke test:**

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod "http://localhost:8000/campaigns?page_size=5"
Invoke-RestMethod http://localhost:8000/stats
```

**Deploy on Render:** use `backend/render.yaml`; mount persistent disk for `DB_PATH=/var/data/givefund.db` and copy or sync the DB from scraper runs.

## 3. Frontend

Open `frontend/index.html` in a browser (or serve statically). Set `API_URL` at the top of the script if the backend is not on `http://localhost:8000`.

For live data, start the backend first. If the API is down, the page shows six built-in sample campaigns.

## Integration checklist

1. `python seed_db.py` or `python main.py --platform gofundme` → rows in `givefund.db`
2. `uvicorn main:app` → `GET /health` shows `campaign_count > 0`
3. `GET /campaigns` returns campaigns with `funding_gap` and `pct_funded`
4. Open `frontend/index.html` → cards load from API; **Give Now** opens `campaign_url` in a new tab

## What to build next

- Tune LaunchGood/Fundly selectors against live DOM; add retry/backoff for rate limits
- CI: seed DB + pytest for backend contract tests
- Host frontend on Netlify/Vercel; point `API_URL` at production API
- Cron on Render/Railway for `scheduler.py` + scraper artifact upload to API disk
- Campaign detail page (optional) — list-only UI today
- Full-text search (SQLite FTS5) if catalog grows large

## Repo layout

```
scraper/          Playwright scrapers, main.py, scheduler.py, seed_db.py
  platforms/      gofundme.py, launchgood.py, fundly.py
backend/          FastAPI main.py, db.py, models.py, render.yaml
frontend/         index.html (all CSS/JS inline)
givefund.db       Shared SQLite (gitignored)
```
