# Sprint Tasks -- Day 1

## API Contract (all agents must respect this shape)

GET /campaigns
  Query params: search (string), category (string), sort_by (string: "most_needed" | "almost_there" | "newest"), page (int, default 1), page_size (int, default 20)
  Response:
  {
    "campaigns": [
      {
        "id": 1,
        "title": "Help Maria with cancer treatment",
        "story_snippet": "Maria is a single mother of two...",
        "photo_url": "https://...",
        "goal_amount": 10000.0,
        "raised_amount": 3200.0,
        "funding_gap": 6800.0,
        "pct_funded": 32.0,
        "platform": "gofundme",
        "campaign_url": "https://gofundme.com/...",
        "category": "medical",
        "scraped_at": "2024-01-15T10:30:00"
      }
    ],
    "total": 142,
    "page": 1,
    "pages": 8
  }

GET /campaigns/{id}
  Response: single Campaign object (same shape as above)

GET /categories
  Response: { "categories": ["medical", "education", "emergency", "community"] }

GET /health
  Response: { "status": "ok", "campaign_count": 142 }

---

## Agent 1 (Scraper) Tasks
- [x] Scaffold /scraper with main.py, scraper.py, db.py, requirements.txt
- [x] Install: playwright, aiosqlite, python-dotenv
- [x] db.py: connect to DB_PATH, create table if not exists, upsert by campaign_url
- [x] scraper.py: Playwright scraper for gofundme.com/discover
- [x] scraper.py: handle category pages /discover/medical-fundraising, /discover/education-fundraising, /discover/emergency-fundraising, /discover/community
- [x] scraper.py: paginate 10 pages per category, random 2-4s delay between pages
- [x] scraper.py: use realistic user agent (Chrome 120 on Mac)
- [x] scraper.py: extract per campaign: title, story_snippet, photo_url, goal_amount, raised_amount, campaign_url, category
- [x] main.py: entry point, accepts --category flag for single category testing
- [ ] Test: python main.py --category medical, confirm rows in givefund.db (run manually -- see Notes)
- [x] Mark tasks done and note row count in Notes below

## Agent 2 (Backend) Tasks
- [ ] Scaffold /backend with main.py, db.py, models.py, requirements.txt
- [ ] Install: fastapi, uvicorn, aiosqlite, python-dotenv
- [ ] db.py: async connect to DB_PATH, all query functions live here only
- [ ] models.py: Pydantic models for Campaign and all response shapes
- [ ] main.py: GET /campaigns with search (ilike title + story_snippet), category filter, sort_by, pagination
- [ ] main.py: GET /campaigns/{id}
- [ ] main.py: GET /categories (distinct values from DB)
- [ ] main.py: GET /health (status + campaign count)
- [ ] main.py: CORS allow all origins
- [ ] Test: uvicorn main:app --reload, hit all endpoints with curl
- [ ] Mark tasks done and note any issues in Notes below

## Agent 3 (Frontend) Tasks
- [ ] Create frontend/index.html as single file with inline CSS and JS
- [ ] Config block at top of JS: const API_URL = "http://localhost:8000"
- [ ] Hero section: site name "GiveFund", tagline, search input
- [ ] Category filter pills: Medical, Education, Emergency, Community
- [ ] Sort dropdown: Most Needed, Almost There, Newest
- [ ] Campaign card grid: 3 col desktop, 2 col tablet, 1 col mobile
- [ ] Campaign card: photo, platform badge, title, story snippet, progress bar, amounts, Give Now button
- [ ] Progress bar color: green >75%, amber >40%, red <40%
- [ ] Give Now button opens campaign_url in new tab
- [ ] Search debounced 400ms
- [ ] Clicking a card expands it inline or navigates to #/campaign/:id view
- [ ] Mock data fallback if API unreachable (3 hardcoded campaigns matching API contract)
- [ ] Mark tasks done in Notes below

## Notes
(agents write here to communicate across boundaries)
- Agent 1 (2026-05-23): All scraper files scaffolded in /scraper. Browser test must be run
  manually -- playwright requires browser binaries. Setup: cd scraper && pip install -r
  requirements.txt && playwright install chromium, then python main.py --category medical
  from repo root (or cd scraper && python main.py --category medical with DB_PATH=../givefund.db).
  Row count: (fill in after manual test). Selector fallbacks in scraper.py handle GoFundMe markup
  changes; if 0 rows are returned check _CARD_SELECTORS list in scraper.py.
- Agent 2: Backend scaffolded in /backend with FastAPI routes, read-only aiosqlite access, Pydantic response models, CORS allow-all, and pinned requirements. Verified with uvicorn and curl against a temporary SQLite database: /health, /campaigns, /campaigns/1, and /categories all return the expected API contract.
