# Scraper platform matrix — scrape everything strategy

**Date:** May 2026  
**Goal:** Index **all** public peer-to-peer and charity crowdfunding listings, not ~20 per platform.  
**Machine-readable registry:** `scraper/platform_registry.json`  
**Live query path:** `scraper/live_search.py` + `GET /search/live?q=`

---

## How we win at scale

| Layer | What it does | Volume |
|-------|----------------|--------|
| **Bulk ingest** | `live_runner.py` — Algolia pagination (GFM), API pages (GlobalGiving), discover scroll | Thousands offline |
| **Live search** | User types *Palestine* / *cancer* → fan-out to **40+ platforms** (shared browser, parallel) | Hundreds per query, ~30–90s |
| **Persist** | `?persist=true` on `/search/live` or `--persist` on CLI | Grows DB from real demand |

**20 per platform is a config floor, not a ceiling.** Set `DISCOVER_MAX_CAMPAIGNS=200`, `GFM_MAX_ALGOLIA_PAGES=60`, `LAUNCHGOOD_MAX_ENRICH=120`.

---

## Scrape method tiers

| Tier | Method | Token / key | Example platforms |
|------|--------|-------------|-------------------|
| **A** | Official REST API | `GLOBALGIVING_API_KEY`, future `KIVA_API_KEY` | GlobalGiving, Kiva (loans) |
| **B** | Public search index (Algolia) | `GFM_ALGOLIA_APP_ID`, `GFM_ALGOLIA_API_KEY` (capture from browser or env) | GoFundMe |
| **C** | Platform search URL + Playwright | None | JustGiving, Ketto, LaunchGood, Chuffed, Givebutter, Milaap, … |
| **D** | Discover / listing pages | None | M-Changa, Thundafund, Islamic Relief CA leaderboard |
| **E** | Sitemap / RSS (backlog) | None | Some WordPress-powered sites |
| **F** | Blocked / org-only | N/A | Facebook fundraisers, PayPal Giving, Classy, GiveLively |

---

## Tokens & APIs (actionable)

| Platform | Env var | Endpoint / notes |
|----------|---------|------------------|
| **GoFundMe** | `GFM_ALGOLIA_APP_ID`, `GFM_ALGOLIA_API_KEY` | `prod_funds_feed_replica_1` on `e7phe9bb38-dsn.algolia.net`; text search via `query=` param |
| **GlobalGiving** | `GLOBALGIVING_API_KEY` | `GET .../search/projects/summary?q=` + paginated `all/projects/active` |
| **LaunchGood** | — | Public `/search?q=` + `/v4/campaign/{slug}` enrich (no public API key found) |
| **JustGiving** | — | `/search?q=` (may rate-limit; run on GHA) |
| **Ketto** | — | `/search?search=` + dedicated `ketto.py` |
| **Kiva** | `KIVA_API_KEY` (partner) | GraphQL — loans, not donations |
| **Stripe / payments** | `STRIPE_*` | Not for scraping — donor tips only |

**No public API key found (use Tier C/D):** BackaBuddy, Milaap, M-Changa, Chuffed, FundRazr, MightyCause, Give.asia, ImpactGuru, WhyDonate, GoGetFunding, Patreon (memberships), Kickstarter/Indiegogo (product focus).

---

## Implemented in GiveFund today

| Platform | Bulk | Live search |
|----------|------|-------------|
| GoFundMe | Algolia categories | Algolia text |
| LaunchGood | Discover + enrich | `/search?q=` |
| GlobalGiving | API pagination | API `q=` |
| JustGiving, Ketto, BackaBuddy, Milaap, M-Changa, … | Discover | Search URL where configured |
| Islamic Relief CA | Leaderboard | — |
| Fundly | Skipped (redirect) | — |

Run live search locally:

```bash
cd scraper
python live_search.py --q "palestine" --json --limit 40
python live_search.py --q "cancer" --persist
```

API:

```bash
curl "http://127.0.0.1:8000/search/live?q=palestine&limit=60&merge_db=true"
```

---

## Top ~150 platforms (aggregator list)

Sources: fundsforNGOs top-20 nonprofit list, market reports (GoFundMe/Classy/Donorbox), regional NGO guides, `SCRAPER_RESEARCH_GLOBAL.md`.

### Tier 1 — Must index (P2P medical/emergency)

GoFundMe, LaunchGood, JustGiving, GoFundMe Charity (charity.gofundme.com), Fundly, YouCaring (legacy/redirect), Crowdrise (→GFM), FreeFunder, GoGetFunding, FundRazr, Fundly, BackaBuddy, Ketto, Milaap, ImpactGuru, M-Changa, Give.asia, WhyDonate, Chuffed, Givebutter, MightyCause, Donorbox (weak index), GlobalGiving, Islamic Relief CA, Patreon (creator), Zeffy (org forms).

### Tier 2 — Regional / faith / diaspora

Thundafund, GivenGain, BackaBuddy, SnapScan (SA), Givengain, Leetchi (EU), KissKissBankBank, Ulule, HelloAsso (FR), Betterplace (DE), Benevity (corp matching), CAF (UK), Wonderful.org, Localgiving (UK), Neighbourly, GlobalGiving UK, Muslim Hands, Penny Appeal, Human Appeal, UNHCR donate, Oxfam appeals.

### Tier 3 — US nonprofit SaaS (mostly org pages)

Classy, Network for Good, GiveLively, RallyUp, Donately, Qgiv, OneCause, Bloomerang, Kindful, Neon CRM public pages, ActBlue (political), ActBlue charities.

### Tier 4 — Product / equity (lower priority for GiveFund)

Kickstarter, Indiegogo, Seed&Spark, Crowd Supply, Republic, Wefunder, StartEngine, Crowdcube, Seedrs.

### Tier 5 — Blocked or no index

Facebook/Meta fundraisers, Instagram, WhatsApp collections, PayPal Giving Fund directory, Google One Today (sunset), Amazon Smile (sunset), TikTok donate stickers.

### Appendix — names to track (150)

1 GoFundMe · 2 LaunchGood · 3 JustGiving · 4 GlobalGiving · 5 Ketto · 6 Milaap · 7 BackaBuddy · 8 M-Changa · 9 Give.asia · 10 Chuffed · 11 Givebutter · 12 MightyCause · 13 FundRazr · 14 GoGetFunding · 15 Donorbox · 16 Patreon · 17 Fundly · 18 YouCaring · 19 Crowdrise · 20 FreeFunder · 21 ImpactGuru · 22 WhyDonate · 23 Thundafund · 24 GivenGain · 25 Leetchi · 26 KissKissBankBank · 27 Ulule · 28 HelloAsso · 29 Betterplace · 30 Benevity · 31 Classy · 32 Network for Good · 33 GiveLively · 34 RallyUp · 35 Kiva · 36 Zeffy · 37 ActBlue · 38 Wonderful · 39 Localgiving · 40 Neighbourly · 41 Islamic Relief CA · 42 IRUSA iRaise · 43 Muslim Hands · 44 Penny Appeal · 45 Human Appeal · 46 CAF · 47 GlobalGiving UK · 48 SnapScan · 49 Givengain · 50 Seed&Spark · 51 Kickstarter · 52 Indiegogo · 53 Crowd Supply · 54 Republic · 55 Wefunder · 56 StartEngine · 57 Crowdcube · 58 Seedrs · 59 Fundable · 60 Experiment.com · 61 Donately · 62 Qgiv · 63 OneCause · 64 Bloomerang · 65 Kindful · 66 Neon · 67 Tilt (sunset) · 68 Plumfund · 69 Deposit a Gift · 70 Honeyfund · 71 Adopt-a-Drain style civic · 72 OpenCollective · 73 Liberapay · 74 Ko-fi · 75 Buy Me a Coffee · 76 Streamlabs charity · 77 Tiltify · 78 Gamers Outreach · 79 Extra Life · 80 St. Jude dashboards · 81 Pledge (PledgeSports) · 82 Sportfunder · 83 Rally.org · 84 Causes.com (legacy) · 85 Fundraise Up widgets · 86 Raisely · 87 Charitable · 88 Bonfire · 89 Custom Ink Fundraising · 90 Teespring charity · 91 Facebook · 92 Instagram · 93 WhatsApp · 94 PayPal Giving · 95 Google · 96 Amazon · 97 TikTok · 98 GoFundMe Pro · 99 Stripe Climate · 100 Every.org · 101 Groundswell · 102 Deed · 103 Bright Funds · 104 YourCause · 105 CyberGrants · 106 Submittable grants · 107 GoFundMe.org · 108 Pledge.to · 109 Goodworld · 110 Cheerful · 111 FundJournal · 112 Whydonate EU · 113 Steunactie (NL) · 114 Voordekunst · 115 Kentaa · 116 Goteo · 117 Verkami · 118 Migranodearena · 119 Hummingbird · 120 Donadora (MX) · 121 Fondeadora · 122 Eprenz · 123 Catarse (BR) · 124 Benfeitoria · 125 Vakinha (BR) · 126 Galoa · 127 Abacashi · 128 Jaiye · 129 NaijaFund · 130 Farmcrowdy · 131 Slice · 132 Mifuko · 133 Zaad · 134 Eversave · 135 iDonate.ie · 136 Alvarum · 137 Wonderful · 138 JustGiving Ireland · 139 Virgin Money Giving (migrated) · 140 BT MyDonate (sunset) · 141 Golden · 142 CharityMe · 143 GiveSendGo · 144 GiveSendGo Churches · 145 Anedot · 146 WinRed · 147 FundHero · 148 Crowdpac · 149 Omaze · 150 Prizeo.

*Next iteration:* add OpenCollective, Raisely, Every.org, GiveSendGo, Raisely JSON APIs where public.

---

## Research per blocked/hard platform

| Platform | Why hard | Possible path |
|----------|----------|----------------|
| Facebook | Graph API restricted | Meta Content Library partner only — skip |
| PayPal Giving | Charity profiles not P2P URLs | Link org names only |
| Classy / GiveLively | Tenant subdomains | Per-org sitemap if allowed |
| Kickstarter | No public search API | `/discover` HTML + rate limit |
| Patreon | Membership not campaign | Different card UX |

---

## Iteration roadmap

1. **Now:** Live search + matrix doc + raised discover caps  
2. **Week 1:** GFM Algolia + GG API on Render/GHA; persist popular queries  
3. **Week 2:** Add OpenCollective, Every.org, GiveSendGo, Raisely scrapers  
4. **Week 3:** Sitemap crawler for Tier D platforms  
5. **Ongoing:** Monitor zero-yield platforms in `ingest_platform_stats`

---

*Re-run bulk ingest after adding keys. Re-run live search QA for: `palestine`, `cancer`, `gaza`, `medical`, `ukraine`.*
