# Payment Friction Strategy — GiveFund

GiveFund is a **discovery aggregator**, not a payment processor. We reduce friction **without** holding donations.

## Shipped: Express Give

**Flow:** Campaign card → `give.html?id={id}` → official platform checkout.

| Piece | Location |
|-------|----------|
| API | `GET /campaigns/{id}/checkout?email=` |
| Logic | `backend/deep_links.py` |
| UI | `frontend/give.html` |

**What it does:**

- GoFundMe / LaunchGood → `/donate` deep links (skip story page)
- Givebutter, Donorbox, Mightycause, GlobalGiving → `email=` query when supported
- UTM attribution on every outbound URL
- **Link likely** badge when Stripe Link often appears on that host
- Honest copy: GiveFund cannot charge the campaign with our token

## Shipped: Stripe card save (optional, free)

- `POST /wallet/setup` — Checkout **setup mode** (no charge)
- Enrolls donor in **Stripe Link** for other Link-enabled sites (same email)
- Does **not** auto-pay GoFundMe

## Not possible without partnerships

| Ask | Reality |
|-----|---------|
| "Apply our token on GoFundMe" | No third-party token API |
| "One click from GiveFund" | Only Pledge/nonprofit embed or partner SSO |
| GiveFund-branded extension autofill | ToS / compliance risk — do not ship |

See `BYPASS_RESEARCH.md` for full angle analysis.

## Long term

1. **Pledge.to** for nonprofit campaigns (`PLEDGE_RESEARCH.md`)
2. **LaunchGood / GoFundMe** referral or embedded checkout partnerships
3. Measure outbound clicks via UTM before outreach

## Friction ladder

1. Express Give + deep links — **live**
2. Email prefill + Link education — **live**
3. Pledge embed (nonprofit subset) — **pilot**
4. Platform partnerships — **when traffic justifies**
