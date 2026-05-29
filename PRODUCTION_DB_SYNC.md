# Production database sync (24k+ campaigns on Render)

## How it works

1. **GitHub Actions** (`Live Scrape` workflow) runs `scale_ingest.py` and publishes:
   - `givefund.db`
   - `db-manifest.json` (campaign count + sha256)
   to the **`db-latest`** GitHub Release.

2. **Render** downloads that file on every deploy/startup via `DB_DOWNLOAD_URL`.

3. **Background scraper** on Render (`LIVE_SCRAPE=true`) keeps the disk fresh between releases.

## One-time setup

### GitHub Secrets (Actions)

| Secret | Purpose |
|--------|---------|
| `GFM_ALGOLIA_APP_ID` | GoFundMe bulk + live search |
| `GFM_ALGOLIA_API_KEY` | Same |
| `GLOBALGIVING_API_KEY` | Optional GlobalGiving API |
| `RENDER_DEPLOY_HOOK_URL` | Optional — redeploy API after each scrape |

### Render environment

| Variable | Value |
|----------|--------|
| `DB_DOWNLOAD_URL` | `https://github.com/ammar-adam/givefund/releases/download/db-latest/givefund.db` |
| `SCRAPE_ON_START` | `false` (after first successful download) |
| `LIVE_SCRAPE` | `true` |
| `GFM_ALGOLIA_APP_ID` | *(secret)* |
| `GFM_ALGOLIA_API_KEY` | *(secret)* |
| `GIVEFUND_FRONTEND_URL` | Your Vercel/Netlify URL (wallet Stripe redirects) |
| `STRIPE_SECRET_KEY` | Optional wallet |
| `STRIPE_PUBLISHABLE_KEY` | Optional wallet |
| `GOOGLE_CLIENT_ID` | Optional Google Sign-In |

## Run scrape + publish

**Actions → Live Scrape → Run workflow** (first run may take 1–3 hours).

Or locally:

```bash
cd scraper
python scale_ingest.py --target 10000
cd ..
python scripts/publish_db_release.py
gh release upload db-latest givefund.db db-manifest.json --clobber
```

## Verify production

```bash
curl https://YOUR-API.onrender.com/health
curl https://YOUR-API.onrender.com/stats
```

Expect `campaign_count` in the thousands after the first successful download.

## Local test download

```powershell
$env:DB_DOWNLOAD_URL="https://github.com/ammar-adam/givefund/releases/download/db-latest/givefund.db"
$env:DB_PATH=".\givefund-downloaded.db"
python scripts/download_db.py
```

See [PRODUCTION_LAUNCH.md](./PRODUCTION_LAUNCH.md) for the full go-live checklist.
