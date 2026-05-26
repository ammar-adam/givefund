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
| Discover scrapers | ⚠️ | Fragile (DOM); need live yield metrics post-scrape |
| Islamic Relief CA | ⚠️ | Playwright-dependent; verify campaign URL shape in prod |
| GlobalGiving | ⚠️ | Blocked until API key registered |
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
| 3 | `GLOBALGIVING_API_KEY` on Render + GHA secret | Ops | ☐ |
| 4 | `STRIPE_SECRET_KEY` if Link tips enabled | Ops | ☐ |
| 5 | Run full scrape cycle once (`scrape_loop.py --once`) | Data | ☐ |
| 6 | Verify ≥3 new platforms have rows in DB | Data | ☐ |
| 7 | Sync frontend platform list with `platforms_catalog.py` | Eng | ☑ |
| 8 | Update `PRODUCTION.md` yield table after scrape | Eng | ☐ |
| 9 | GHA scrape: add `islamicrelief_ca` + optional discover subset | Eng | ☐ |
| 10 | Manual QA: Give Now opens `/donate` + UTM on GFM/LG | QA | ☐ |
| 11 | Manual QA: mock banner hidden when API up | QA | ☐ |
| 12 | Rate-limit: GFM Algolia creds in GHA secrets | Ops | ☐ |

**Pass 3 verdict:** **Ship discovery MVP** when 1–6 and 10–11 pass. **Ship “global” claim** when 6 + new platform data verified.

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
