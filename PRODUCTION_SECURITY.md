# GiveFund — Production Security Reference

## Secrets (never commit any of these)

| Secret | Where to set | How to generate |
|---|---|---|
| `WALLET_SESSION_SECRET` | Render Environment | `openssl rand -hex 32` |
| `STRIPE_SECRET_KEY` | Render Environment | Stripe Dashboard → Developers → API keys |
| `GOOGLE_CLIENT_ID` | Render Environment | Google Cloud Console → OAuth 2.0 |
| `STRIPE_PUBLISHABLE_KEY` | Vercel Environment Variable | Stripe Dashboard |
| `GIVEFUND_FRONTEND_URL` | Render Environment | `https://givefund.vercel.app` |
| `GIVEFUND_API_URL` | Vercel Environment Variable | Your Render service URL |
| `GH_TOKEN` | GitHub Actions Secret | GitHub → Settings → Developer → PAT |
| `GF_ALGOLIA_APP_ID` | GitHub Actions Secret | GoFundMe Algolia key capture |
| `GF_ALGOLIA_API_KEY` | GitHub Actions Secret | GoFundMe Algolia key capture |

All secrets stored server-side (Render) or in CI (GitHub Actions). Never in frontend JS.

---

## Session tokens

- HMAC-SHA256 signed, no JWT library dependency
- 7-day TTL, verified on every authenticated request
- Stored in `sessionStorage` only (cleared on tab close)
- Secret: `WALLET_SESSION_SECRET` env var on Render

## CORS

- Allowed origins: `GIVEFUND_FRONTEND_URL` + localhost dev ports
- Wildcard (`*`) is never set
- Config in `backend/main.py → _frontend_base_url()`

## Rate limiting

In-memory sliding window, no Redis required:

| Route | Limit |
|---|---|
| `/wallet/*` | 10 req/min per IP |
| `/search/live` | 5 req/min per IP |
| `/search/fast` | 30 req/min per IP |
| All others | 120 req/min per IP |

Returns `429 Too Many Requests` with `Retry-After` header.

## Stripe

- TEST mode only until manually switched to live
- Test card: `4242 4242 4242 4242`, any future date, any CVC
- Setup mode only — no charges ever initiated by GiveFund
- Webhook not required for basic wallet save flow

## Frontend security headers (Vercel)

Set in `vercel.json`:
- `Strict-Transport-Security` — HSTS 2 years + preload
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` — allowlists Google Sign-In, Stripe, fonts only

## Database

- Campaign DB: downloaded from GitHub Release `db-latest` at boot
- Donor profiles: stored in persistent disk at `/var/data/givefund.db` on Render
- **Donor profiles are NOT included in the `db-latest` release** (see scrape.yml)
- The SQLite file on Render's persistent disk is the only copy of donor data

## Checklist before going live

- [ ] `WALLET_SESSION_SECRET` set (≥ 32 random bytes)
- [ ] `STRIPE_SECRET_KEY` set (sk_test_ for now)
- [ ] `GOOGLE_CLIENT_ID` set + redirect URIs include production domain
- [ ] `GIVEFUND_FRONTEND_URL` = `https://givefund.vercel.app` on Render
- [ ] `GIVEFUND_API_URL` set on Vercel
- [ ] All pytest tests pass (`python -m pytest backend/tests/ -q`)
- [ ] CORS check: `curl -H "Origin: https://evil.com" <api>/health` → no ACAO header
- [ ] CSP headers present: `curl -I https://givefund.vercel.app` → check `content-security-policy`
