# GiveFund — Production Deployment

**Start here:** [PRODUCTION_LAUNCH.md](./PRODUCTION_LAUNCH.md) — step-by-step checklist with every env var.

## One-click API (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ammar-adam/givefund)

Uses root [`render.yaml`](render.yaml). On boot:

1. Downloads `givefund.db` from GitHub Release (`DB_DOWNLOAD_URL`) when available
2. Runs scale ingest only if DB &lt; `MIN_CAMPAIGNS` (10k)
3. Starts background live scraper (`LIVE_SCRAPE=true`)
4. Serves FastAPI on `$PORT`

## Frontend (Vercel) — recommended

1. [Import repo](https://vercel.com/new) → `ammar-adam/givefund`
2. Framework: **Other** (static). `vercel.json` runs `scripts/write-frontend-config.js`.
3. **Environment variables** (Production + Preview):

   | Variable | Example |
   |----------|---------|
   | `GIVEFUND_API_URL` | `https://givefund-api.onrender.com` |

   HTTPS, no trailing slash.

4. Deploy → stats bar shows live counts.

## Frontend (Netlify)

Same `GIVEFUND_API_URL`; see [`netlify.toml`](netlify.toml).

## Architecture

| Component | Host | Notes |
|-----------|------|-------|
| API + SQLite | Render | Persistent disk `/var/data/givefund.db` |
| Frontend | Vercel / Netlify | `GIVEFUND_API_URL` → Render API |
| DB snapshots | GitHub Release `db-latest` | Live Scrape workflow every 4h |
| Wallet (optional) | Stripe + Google | Setup mode only — no GiveFund charges |

## Environment variables (summary)

| Where | Keys |
|-------|------|
| **Render** | `GFM_ALGOLIA_*`, `GIVEFUND_FRONTEND_URL`, optional `STRIPE_*`, `GOOGLE_CLIENT_ID`, `GLOBALGIVING_API_KEY` |
| **GitHub Actions** | Same Algolia keys, optional `RENDER_DEPLOY_HOOK_URL` |
| **Vercel** | `GIVEFUND_API_URL` |

Full table in [PRODUCTION_LAUNCH.md](./PRODUCTION_LAUNCH.md).

## Data refresh

1. **GitHub Actions** — [`scrape.yml`](.github/workflows/scrape.yml) every 4h publishes `givefund.db` to release **`db-latest`**
2. **Render** — downloads on deploy/startup; background `live_runner.py` keeps disk fresh
3. **Optional** — `RENDER_DEPLOY_HOOK_URL` secret redeploys API after each scrape

See [PRODUCTION_DB_SYNC.md](./PRODUCTION_DB_SYNC.md).

## Scraper scale (typical)

| Platform | Method | Typical yield |
|----------|--------|---------------|
| GoFundMe | Algolia pagination | **20k+** with keys |
| Open Collective | GraphQL | **100+** |
| LaunchGood | Discover + enrich | **20–50** |
| Givebutter, JustGiving, Ketto, … | Discover + live search | **varies** |
| GlobalGiving | REST API (key) | **100+** |

**25 platforms** in catalog; indexed count depends on scrape runs.

## Verify production

```bash
curl https://YOUR-API.onrender.com/health
curl https://YOUR-API.onrender.com/stats
curl https://YOUR-API.onrender.com/wallet/config
curl "https://YOUR-API.onrender.com/campaigns?page_size=3"
```

Open frontend URL — no mock banner when API is reachable.

## CI

Every push runs [`ci.yml`](.github/workflows/ci.yml) (API + deep-link tests).
