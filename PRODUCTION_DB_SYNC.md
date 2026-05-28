# Production database sync (24k+ campaigns on Render)

## How it works

1. **GitHub Actions** (`Live Scrape` workflow) runs `scale_ingest.py` and publishes:
   - `givefund.db`
   - `db-manifest.json` (campaign count + sha256)
   to the **`db-latest`** GitHub Release.

2. **Render** downloads that file on every deploy/startup via `DB_DOWNLOAD_URL`.

3. **Background scraper** on Render (`LIVE_SCRAPE=true`) keeps the disk fresh between releases.

## One-time Render setup

In the Render dashboard for `givefund-api`:

| Variable | Value |
|----------|--------|
| `DB_DOWNLOAD_URL` | `https://github.com/ammar-adam/givefund/releases/download/db-latest/givefund.db` |
| `SCRAPE_ON_START` | `false` (after first successful download) |
| `LIVE_SCRAPE` | `true` |
| `GFM_ALGOLIA_APP_ID` | *(secret)* |
| `GFM_ALGOLIA_API_KEY` | *(secret)* |

Optional: **`RENDER_DEPLOY_HOOK_URL`** — Render deploy hook; add as GitHub secret so each scrape run redeploys the API with the new DB.

## Run scrape + publish manually

```bash
cd scraper
python scale_ingest.py --target 10000
cd ..
python scripts/publish_db_release.py
gh release upload db-latest givefund.db db-manifest.json --clobber
```

Or: **Actions → Live Scrape → Run workflow**.

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
