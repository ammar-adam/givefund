# Production QA — Three-Pass Audit

**Date:** May 2026  
**Scope:** GiveFund discovery aggregator (API + static frontend + scrapers)

---

## Pass 1 — Baseline (pre-expansion)

**Checked:** `main` branch, local API on `:8000`, CI workflow, Render/Vercel docs.

| Area | Status | Finding |
|------|--------|---------|
| API health | ✅ | `/health` returns `ok`, ~4315 campaigns |
| API contract tests | ✅ | 10/10 pytest pass |
| Platform coverage | ⚠️ | DB only has `gofundme`, `launchgood`, `fundly` — 12 platforms in UI catalog but 9+ scrapers unwired |
| Scraper registry | ❌ | `discover.py` / `extra.py` existed untracked; `__init__.py` only registered 3 platforms |
| Stripe Link checkout | ⚠️ | Shipped on `main`; requires `STRIPE_SECRET_KEY` in prod — optional feature |
| Frontend deploy | ⚠️ | `GIVEFUND_API_URL` must be HTTPS on Vercel; mock banner if API down |
| GlobalGiving API | ❌ | No `GLOBALGIVING_API_KEY` in env |
| CI scrape workflow | ⚠️ | GHA only runs GoFundMe + LaunchGood |
| E2E tests | ❌ | No Playwright/Cypress for Give Now links |
| Monitoring | ❌ | No uptime/alerting on Render |
| Legal/ToS | ⚠️ | Discover scrapers need per-site robots review |

**Pass 1 verdict:** **Not production-complete** for “global discovery” promise — strong US P2P index, weak developing-country data.

---

## Pass 2 — After scraper expansion (this commit)

**Changes applied:**

- Registered **18** platform scrapers in `scraper/platforms/__init__.py`
- Added **Islamic Relief CA** dedicated scraper (`islamicrelief.py`)
- Added **GlobalGiving** API scraper (`globalgiving.py`, key-gated)
- Added discover configs: **Ketto, M-Changa, BackaBuddy, Give.asia, Thundafund**
- Added `scripts/scrape_loop.py` for continuous rotation
- Updated `backend/platforms_catalog.py` to 18 platforms
- Documented global research in `SCRAPER_RESEARCH_GLOBAL.md`

| Area | Status | Finding |
|------|--------|---------|
| Scraper registry | ✅ | All platforms wired |
| Discover scrapers | ⚠️ | Fragile (DOM); BackaBuddy fixed via HTML path regex (8+ campaigns) |
| Islamic Relief CA | ⚠️ | Playwright + API JSON capture; verify URL slugs |
| GlobalGiving | ✅ | HTML discover fallback when API key missing |
| BackaBuddy | ✅ | Dedicated `backabuddy.py` (regex on rendered HTML) |
| Ketto | ⚠️ | Often blocked locally; run on GHA |
| LaunchGood | ⚠️ | Network timeouts locally; 120s timeout + `/explore` fallback |
| Background ingest | ✅ | `scrape_loop.py` available |
| CI | ⚠️ | Still 2-platform daily job — expand or use artifact DB sync |
| Frontend catalog sync | ✅ | 18-entry fallback + `/platforms/catalog` API sync |

**Pass 2 verdict:** **Architecture ready**; **data** still needs scrape cycles + API keys.

---

## Pass 3 — Final gate (ship checklist)

| # | Requirement | Owner | Done? |
|---|-------------|-------|-------|
| 1 | Render API live + `/health` 200 | Ops | ☐ |
| 2 | Vercel `GIVEFUND_API_URL` → Render HTTPS | Ops | ☐ |
| 3 | `GFM_ALGOLIA_*` on Render + GHA secrets | Ops | ☐ |
| 4 | Run **Live Scrape** workflow once → `db-latest` release | Data | ☐ |
| 5 | Render `GIVEFUND_FRONTEND_URL` = Vercel URL | Ops | ☐ |
| 6 | Optional: `STRIPE_*` + `GOOGLE_CLIENT_ID` for wallet | Ops | ☐ |
| 7 | `GLOBALGIVING_API_KEY` on Render + GHA (optional) | Ops | ☐ |
| 8 | Verify ≥10k campaigns via `/stats` | Data | ☐ |
| 9 | Manual QA: Express Give → official `/donate` + UTM | QA | ☐ |
| 10 | Manual QA: mock banner hidden when API up | QA | ☐ |
| 11 | Manual QA: `/wallet.html` Stripe redirect (if keyed) | QA | ☐ |

**Pass 3 verdict:** Follow [PRODUCTION_LAUNCH.md](./PRODUCTION_LAUNCH.md) — ship when 1–5 and 9–10 pass.

---

## Risk register (unchanged priorities)

1. **GoFundMe Algolia** — keys expire; local scrape fails without `GFM_ALGOLIA_*`  
2. **Discover scraper breakage** — silent zero-yield platforms  
3. **Stripe** — marketing must not imply GiveFund processes campaign donations  
4. **ToS** — throttle scrapers; respect robots.txt where present  

---

## Recommended production commands

```bash
# One full ingestion cycle (2–4 hours with GoFundMe)
python scripts/scrape_loop.py --once

# Continuous (background server)
python scripts/scrape_loop.py --interval 7200

# Verify
curl -s http://127.0.0.1:8000/stats | jq
sqlite3 givefund.db "SELECT platform, COUNT(*) FROM campaigns GROUP BY platform;"
```

---

*Re-run this checklist after each major scraper or deploy change.*
