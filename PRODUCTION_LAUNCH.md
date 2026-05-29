# Production launch checklist

Use this once before going live. GiveFund runs **free** — you only pay for Render/Vercel hosting and optional Stripe/Google (no per-donation fees from us).

## Architecture

| Piece | Host | URL example |
|-------|------|-------------|
| API + SQLite | [Render](https://render.com) | `https://givefund-api.onrender.com` |
| Static UI | [Vercel](https://vercel.com) or Netlify | `https://givefund.vercel.app` |
| Campaign DB snapshot | GitHub Release `db-latest` | Built by **Live Scrape** workflow |

## How data stays fresh (read this)

There are **two** scrape loops — both need `GFM_ALGOLIA_*` keys or GoFundMe indexing stalls:

| Loop | Where | Schedule | What it does |
|------|-------|----------|--------------|
| **Live loop** | Render server | Every **20 min** (`LIVE_SCRAPE=true`) | `live_runner.py` updates the DB on disk that the API reads **right now** |
| **Snapshot loop** | GitHub Actions | **Hourly** incremental + **daily** full rebuild | Publishes `db-latest` release; optional deploy hook refreshes Render |

`SCRAPE_ON_START=false` only skips the one-time bootstrap ingest on deploy — it does **not** turn off the live loop.

On every Render boot: download release **only if** local DB has fewer campaigns than the remote snapshot (won't overwrite fresher data).

**Without Algolia keys on Render**, the live loop runs but GoFundMe yield is ~zero — set keys on Render **and** GitHub Secrets.

---

## Step 1 — Deploy API (Render)

1. [Deploy from repo](https://render.com/deploy?repo=https://github.com/ammar-adam/givefund) or connect the GitHub repo with root `render.yaml`.
2. Wait for first deploy (may take ~10 min — Playwright install).
3. Copy the service URL → `https://YOUR-API.onrender.com`.

### Render environment variables

Set these in **Dashboard → givefund-api → Environment** (secrets marked *secret*):

| Variable | Required | Notes |
|----------|----------|-------|
| `DB_DOWNLOAD_URL` | Yes | Already in `render.yaml` — points at GitHub Release |
| `SCRAPE_ON_START` | Yes | `false` after first DB download (default in blueprint) |
| `LIVE_SCRAPE` | Yes | `true` — background ingest on disk |
| `GFM_ALGOLIA_APP_ID` | Yes* | *Required for fresh scrapes; capture from browser DevTools on gofundme.com/discover |
| `GFM_ALGOLIA_API_KEY` | Yes* | Same capture session |
| `GLOBALGIVING_API_KEY` | Optional | [Register free](https://www.globalgiving.org/api/) — adds 100+ campaigns |
| `GIVEFUND_FRONTEND_URL` | Yes | Your Vercel/Netlify URL **no trailing slash** — Stripe wallet redirects |
| `STRIPE_SECRET_KEY` | Optional | Wallet: save card (setup mode, no charge) |
| `STRIPE_PUBLISHABLE_KEY` | Optional | Paired with secret key |
| `GOOGLE_CLIENT_ID` | Optional | Google Sign-In on wallet page |

Verify:

```bash
curl https://YOUR-API.onrender.com/health
curl https://YOUR-API.onrender.com/stats
```

Expect `campaign_count` in the thousands after Step 3.

---

## Step 2 — Deploy frontend (Vercel recommended)

1. [Import repo](https://vercel.com/new) → `ammar-adam/givefund`.
2. Framework: **Other** (static). Root `vercel.json` handles the build.
3. Environment variable (Production + Preview):

   ```
   GIVEFUND_API_URL=https://YOUR-API.onrender.com
   ```

   HTTPS only, no trailing slash.

4. Deploy and open the site. Stats bar should show live counts (no mock banner).

**Netlify:** same `GIVEFUND_API_URL`; see `netlify.toml`.

---

## Step 3 — Publish campaign database (GitHub Actions)

1. Add GitHub repo **Secrets** (Settings → Secrets → Actions):

   | Secret | Value |
   |--------|--------|
   | `GFM_ALGOLIA_APP_ID` | From GoFundMe browser capture |
   | `GFM_ALGOLIA_API_KEY` | Same |
   | `GLOBALGIVING_API_KEY` | Optional |
   | `RENDER_DEPLOY_HOOK_URL` | Optional — Render deploy hook URL so each scrape redeploys API |

2. **Actions → Live Scrape → Run workflow** (first run ~1–3 hours).
3. Confirm release exists: `https://github.com/ammar-adam/givefund/releases/tag/db-latest`
4. Trigger Render **Manual Deploy** (or wait for deploy hook) so API downloads the new DB.

---

## Step 4 — Wallet + Google (optional)

### Stripe (save card, no charge)

1. [Stripe Dashboard](https://dashboard.stripe.com) → Developers → API keys.
2. Set `STRIPE_SECRET_KEY` and `STRIPE_PUBLISHABLE_KEY` on Render.
3. Set `GIVEFUND_FRONTEND_URL` to your Vercel URL (must match wallet redirect URLs).
4. Test: open `https://YOUR-SITE/wallet.html` → save card → return to `wallet-success.html`.

### Google Sign-In

1. [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create **OAuth 2.0 Client ID** → type **Web application**.
3. **Authorized JavaScript origins:** your Vercel URL (e.g. `https://givefund.vercel.app`).
4. Copy Client ID → Render `GOOGLE_CLIENT_ID`.
5. Test Google button on `/wallet.html`.

GiveFund **never** charges campaign donations. Wallet only enables Stripe Link autofill on third-party checkouts where supported.

---

## Step 5 — Smoke test (production)

```bash
API=https://YOUR-API.onrender.com
SITE=https://YOUR-SITE.vercel.app

curl -sf "$API/health" | jq .
curl -sf "$API/stats" | jq .
curl -sf "$API/wallet/config" | jq .
curl -sf "$API/platforms/catalog" | jq .count
curl -sf "$API/campaigns/1/checkout?email=test@example.com" | jq .donate_url
```

Manual:

- [ ] Search “Palestine” or “medical” — results load, counts make sense
- [ ] **Give now** → Express Give page → opens official `/donate` URL
- [ ] Wallet page loads; Stripe redirect works if keys set
- [ ] No mock-data banner when API is up

---

## Ongoing ops

| Task | Frequency |
|------|-----------|
| Render live loop | Every **20 min** (automatic while API is up) |
| GHA incremental scrape | **Hourly** (`live_runner` + publish `db-latest`) |
| GHA full scale ingest | **Daily** 06:00 UTC |
| Rotate GFM Algolia keys | When scrape yield drops to zero |
| Render redeploy | Optional deploy hook after each GHA run |

See also: [PRODUCTION.md](./PRODUCTION.md), [PRODUCTION_DB_SYNC.md](./PRODUCTION_DB_SYNC.md), [PRODUCTION_QA.md](./PRODUCTION_QA.md).
