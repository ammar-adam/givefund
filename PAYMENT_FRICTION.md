# Payment Friction Strategy — GiveFund

GiveFund is a **discovery aggregator**, not a payment processor. This document describes how we reduce friction for donors without becoming a money transmitter.

## Current State (Shipped)

### Smart deep linking

`buildDonateUrl(campaign)` in `frontend/index.html` sends donors to the **lowest-step** public URL per platform:

| Platform | Behavior |
|----------|----------|
| **GoFundMe** | `https://www.gofundme.com/f/{slug}/donate` — skips the story page |
| **LaunchGood** | `https://www.launchgood.com/v4/campaign/{slug}/donate` — slug from `/project/` or `/v4/campaign/` URLs |
| **Fundly** | Campaign URL only (no reliable public `/donate` pattern) |
| **All others** | `campaign_url` fallback |

**Trust copy:** Under “Give now”, secondary 12px text: *“You'll be taken to {Platform} to complete your donation.”*

### Why this matters

- One fewer click on high-volume platforms (GoFundMe, LaunchGood).
- Honest expectations → fewer abandoned tabs and more trust.
- No payment liability on GiveFund; funds never touch our stack.

## Near Term: Pledge API (Nonprofit Subset)

See `PLEDGE_RESEARCH.md` for full analysis.

**Summary:** [Pledge](https://www.pledge.to/products/apis) enables embedded donation forms and APIs for **verified nonprofits**, not arbitrary personal GoFundMe campaigns.

**When to use:**

- Campaigns classified as charity / nonprofit with a resolvable **EIN** or Pledge organization ID.
- Platforms already nonprofit-native (e.g. GlobalGiving, some Donorbox org campaigns).

**When not to use:**

- Personal medical, emergency, family, and most peer-to-peer fundraisers.

**Pilot plan:**

1. Sandbox API key from Pledge support.
2. Single nonprofit campaign row → `plg-donate` embed with `data-ein` or API fundraiser ID.
3. A/B or toggle: “Donate on GiveFund” vs “Donate on GoFundMe” for eligible rows only.

## Long Term: Native Platform Partnerships

Target platforms with meaningful GiveFund referral volume:

| Partner | Ask |
|---------|-----|
| **LaunchGood** | Referral API, donate deep-link params, or embedded checkout for referred traffic |
| **Fundly** | Public listing API + donate URL contract (Fundly currently weak in scraper) |
| **GoFundMe** | Unlikely full API; pursue official **discover/affiliate** or UTM partner program for `/donate` links |

**Pitch once we have traffic:**

> “GiveFund sends you donors who already chose a campaign. We index {N} campaigns across {M} platforms. Give us API access or rev-share so donors can complete payment without leaving our experience — or formalize referral attribution for deep links.”

**Metrics to track before outreach:**

- Clicks on “Give now” per platform (UTM: `utm_source=givefund&utm_medium=referral`)
- Top campaigns by outbound clicks
- Bounce rate return (if measurable via partner)

## Friction Ladder (Priority Order)

1. **Deep link to `/donate`** — live (GoFundMe, LaunchGood).
2. **UTM + analytics** — attribute outbound traffic for partnership conversations.
3. **Pledge embed** — nonprofit-only rows with EIN metadata.
4. **Partner APIs** — LaunchGood / Fundly first (aligned with existing scrapers).
5. **On-site wallet / accounts** — out of scope for GiveFund mission (no accounts, no fees).

## Non-Goals

- Holding donor payment credentials
- Becoming a 501(c)(3) fiscal sponsor
- Routing Pledge donations to personal GoFundMe balances
- Replacing platform trust/compliance flows

## Files

| File | Role |
|------|------|
| `frontend/index.html` | `buildDonateUrl`, donate hint UI |
| `PLEDGE_RESEARCH.md` | Third-party API investigation |
| `PAYMENT_FRICTION.md` | This strategy doc |
