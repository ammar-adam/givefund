# Sprint Tasks — GiveFund Orchestrator

## API Contract (all agents must respect this shape)

GET /campaigns — search, category, platform, sort_by (most_needed | almost_there | newest), page, page_size  
GET /campaigns/{id}  
GET /categories  
GET /platforms  
GET /stats  
GET /health  

Campaign fields include: id, title, story_snippet, photo_url, goal_amount, raised_amount, funding_gap, pct_funded, platform, campaign_url, category, location, scraped_at

---

## Agent 1 (Scraper) Tasks
- [x] Multi-platform structure under `scraper/platforms/` (gofundme, launchgood, fundly)
- [x] CLI: `python main.py --platform all|gofundme|launchgood|fundly` and `--category` for GoFundMe
- [x] Playwright scrapers with 2–5s delays, realistic user agent, per-card try/except
- [x] Paginate 5 pages per category/platform
- [x] Upsert by campaign_url; DB schema with location + indexes
- [x] `scheduler.py` — 24h schedule via `schedule` library
- [x] `seed_db.py` for local dev when sites block scraping
- [x] Live scrape verified: GoFundMe Algolia (~15/run), LaunchGood v4 (~18/run); Fundly skipped (redirect)

## Agent 2 (Backend) Tasks
- [x] FastAPI with aiosqlite read-only access
- [x] All API contract endpoints including /platforms and /stats
- [x] Platform filter, location field, computed funding_gap and pct_funded
- [x] sort_by almost_there excludes fully funded campaigns
- [x] CORS allow all; request logging middleware; 422 validation messages
- [x] `render.yaml` for Render deployment
- [x] Verified: /health campaign_count=6, /campaigns returns shaped Campaign objects

## Agent 3 (Frontend) Tasks
- [x] Single-file `frontend/index.html` — dark editorial design per orchestrator spec
- [x] Sticky nav, hero, stats bar, category pills, sort + platform filters
- [x] Campaign grid with skeleton loading, coral progress bar, Give Now links
- [x] 400ms debounced search; 6-campaign mock fallback
- [x] API_URL config at top of script block

## Notes
- **2026-05-25 Orchestrator**: Full stack integrated. DB seeded with 6 sample campaigns for verification when live scraping is blocked. Playwright 1.44 may fail to build on Python 3.13 without MSVC — use Python 3.11 or install build tools, then `playwright install chromium`.
- **Git**: single branch `main` only (agent/* branches removed).
- **Prod deploy**: See PRODUCTION.md — Render API, Netlify frontend, GHA daily scrape artifact.
- **Partial**: Fundly has no public listing URL. GoFundMe returns overlapping hits across categories (~15 unique) until scroll/pagination is improved.
