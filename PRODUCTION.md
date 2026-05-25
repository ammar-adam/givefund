# GiveFund — Production Deployment

## One-click API (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ammar-adam/givefund)

Uses root [`render.yaml`](render.yaml). On first boot, `scripts/start_prod.sh` scrapes GoFundMe + LaunchGood if the DB has fewer than 50 campaigns.

After deploy, copy your service URL (e.g. `https://givefund-api.onrender.com`).

## Frontend (Netlify)

1. [Import repo](https://app.netlify.com/start) → pick `ammar-adam/givefund`
2. Build settings (from `netlify.toml`): base `frontend`, publish `.`
3. Environment variable:
   ```
   GIVEFUND_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
   ```
4. Deploy

## Architecture

| Component | Host | Notes |
|-----------|------|-------|
| API + SQLite | Render | Persistent disk `/var/data/givefund.db` |
| Frontend | Netlify | `GIVEFUND_API_URL` → Render API |
| Scraper | Render boot + GitHub Actions | ~1000+ GoFundMe via Algolia pagination |

## Data refresh

**Automatic on Render:** set `SCRAPE_ON_START=true` (default). Re-deploy to re-scrape if needed.

**Daily GitHub Actions:**

- [`scrape.yml`](.github/workflows/scrape.yml) — 06:00 UTC, uploads `givefund.db` artifact
- [`publish-db.yml`](.github/workflows/publish-db.yml) — pushes DB to `data` branch

**Pull DB on startup without scraping:**

Set on Render:

```
DB_DOWNLOAD_URL=https://raw.githubusercontent.com/ammar-adam/givefund/data/data/givefund.db
SKIP_DB_DOWNLOAD=false
SCRAPE_ON_START=false
```

(First `data` branch publish happens after the first successful daily scrape workflow.)

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
