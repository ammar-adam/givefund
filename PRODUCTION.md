# GiveFund — Production Deployment

## Architecture

| Component | Host | Notes |
|-----------|------|-------|
| API + SQLite | [Render](https://render.com) | `backend/render.yaml`, disk at `/var/data/givefund.db` |
| Frontend | [Netlify](https://netlify.com) | `netlify.toml`, set `GIVEFUND_API_URL` |
| Scraper | GitHub Actions + Render boot | Daily workflow + scrape on deploy if DB sparse |

## 1. Deploy API (Render)

1. Connect repo `ammar-adam/givefund` on Render.
2. Use blueprint `backend/render.yaml` or create a **Web Service**:
   - Root directory: `backend`
   - Build: `pip install -r requirements.txt && pip install -r ../scraper/requirements.txt && playwright install chromium`
   - Start: `bash ../scripts/start_prod.sh`
   - Add disk: 1GB at `/var/data`
   - Env: `DB_PATH=/var/data/givefund.db`
3. Optional: `DB_DOWNLOAD_URL` — HTTPS URL to a `givefund.db` file (e.g. from GitHub Actions artifact hosting).
4. Note the service URL, e.g. `https://givefund-api.onrender.com`.

On first deploy, `start_prod.sh` runs GoFundMe + LaunchGood scrapers if fewer than 10 campaigns exist.

## 2. Deploy frontend (Netlify)

1. New site from Git, base directory `frontend` (or use repo root with `netlify.toml`).
2. Set environment variable:
   ```
   GIVEFUND_API_URL=https://givefund-api.onrender.com
   ```
3. Build command (from `netlify.toml`) writes `config.js` with that URL.
4. Deploy — donors hit Netlify; API calls go to Render.

## 3. Keep data fresh

**GitHub Actions** (`.github/workflows/scrape.yml`):

- Runs daily at 06:00 UTC and on manual dispatch.
- Uploads `givefund.db` artifact (14-day retention).
- Download artifact after a run and set `DB_DOWNLOAD_URL` on Render, or copy to disk manually.

**On-server scheduler** (optional VM):

```bash
cd scraper && python scheduler.py
```

## 4. Fundly status

`fundly.com/explore` redirects to SignUpGenius — no public listing. Fundly is skipped until a stable URL exists. GoFundMe (Algolia) and LaunchGood are production sources.

## 5. Verify production

```bash
curl https://YOUR-API.onrender.com/health
curl "https://YOUR-API.onrender.com/campaigns?page_size=3"
```

Open Netlify URL — stats bar should show live counts, not the mock banner.

## 6. CI

Every push runs `backend/tests` via `.github/workflows/ci.yml`.
