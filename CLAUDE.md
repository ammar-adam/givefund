# GiveFund

A public service crowdfunding aggregator. Lets donors search for individual people raising money across GoFundMe and other platforms in one place. No monetization. No accounts. Just discovery.

## Stack
- Scraper: Python 3.11, Playwright, aiosqlite
- Backend: Python 3.11, FastAPI, aiosqlite, uvicorn
- Frontend: Plain HTML + CSS + vanilla JS (no build tool, no npm)
- Database: SQLite (local file: givefund.db at repo root)
- Deploy later: Render (backend), Vercel or Netlify (frontend)

## Database Schema
```sql
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
);
```

funding_gap and pct_funded are computed in Python at query time, not stored in DB.

## Env Vars
Read from root .env using python-dotenv. Never commit .env.
```
PORT=8000
DB_PATH=./givefund.db
```

Frontend reads API base URL from a config block at the top of index.html:
```js
const API_URL = "http://localhost:8000";
```

## Rules
- Never touch files outside your designated directory (see AGENTS.md)
- All secrets via environment variables, never hardcoded
- No external component libraries, no npm, no build tools on the frontend
- Every function needs a docstring or inline comment
- Log errors with context, never silently swallow them
- All agents share the same givefund.db file at repo root -- scraper writes, backend reads
