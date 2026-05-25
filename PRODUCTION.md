# GiveFund — Production Deployment

## One-click API (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ammar-adam/givefund)

Uses root [`render.yaml`](render.yaml). On first boot, `scripts/start_prod.sh` scrapes GoFundMe + LaunchGood if the DB has fewer than 50 campaigns.

After deploy, copy your service URL (e.g. `https://givefund-api.onrender.com`).

## Frontend (Vercel) — recommended for UI

1. [Import repo](https://vercel.com/new) → `ammar-adam/givefund`
2. Framework preset: **Other** (static). Root `vercel.json` is already in the repo.
3. **Environment variable** (Production + Preview):
   ```
   GIVEFUND_API_URL=https://YOUR-API-HOST.onrender.com
   ```
   Must be **HTTPS**. No trailing slash.
4. Deploy → open the Vercel URL. Stats bar should show live counts (not the mock banner).

## Frontend (Netlify)

Same env var; see `netlify.toml` if you prefer Netlify over Vercel.

## Architecture

| Component | Host | Notes |
|-----------|------|-------|
| API + SQLite | Render | Persistent disk `/var/data/givefund.db` |
| Frontend | Netlify | `GIVEFUND_API_URL` → Render API |
| Scraper | Render boot + GitHub Actions | ~1000+ GoFundMe via Algolia pagination |

## Data refresh

**Automatic on Render:** set `SCRAPE_ON_START=true` (default). Re-deploy to re-scrape if needed.

**Daily GitHub Actions:**

- [`scrape.yml`](.github/workflows/scrape.yml) — 06:00 UTC, uploads `givefund.db` as a workflow artifact (download from Actions tab if needed)

**Optional:** set `DB_DOWNLOAD_URL` on Render to any HTTPS URL hosting a `givefund.db` snapshot, with `SCRAPE_ON_START=false`.

## Scraper scale (verified)

| Platform | Method | Typical yield |
|----------|--------|---------------|
| GoFundMe | Algolia pagination (50/page × 5 pages × 4 categories) | **~1000+** unique |
| LaunchGood | Discover + page enrichment | **~18–50** |
| Fundly | No public listing (redirect) | skipped |

## Verify production

```bash
curl https://YOUR-API.onrender.com/health
curl "https://YOUR-API.onrender.com/stats"
curl "https://YOUR-API.onrender.com/campaigns?page_size=3"
```

Open Netlify URL — stats bar shows live totals; mock banner should not appear.

## CI

Every push runs [`ci.yml`](.github/workflows/ci.yml) (API contract tests).
