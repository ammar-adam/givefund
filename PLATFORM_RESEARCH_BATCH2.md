# Platform research — batch 2 (May 2026)

**Catalog size:** 42 platforms (up from 25)  
**Live search:** 35+ with search URL or API (parallel, shared browser)

## Added this batch

| Platform | Region | Search method | Notes |
|----------|--------|---------------|-------|
| FreeFunder | US | `/search?q=` | P2P medical/emergency |
| Plumfund | US | `/search?q=` | Registry / gift funds |
| Ko-fi | Global | `/explore?search=` | Creator support (not always P2P medical) |
| Liberapay | EU | Browse `/explore/public` | Recurring patronage |
| HelloAsso | France | `/associations/recherche?query=` | Associations + collectes |
| Betterplace | Germany | `/en/search?q=` | Charity projects |
| iDonate | Ireland | `/f?s=` | Irish fundraisers |
| Steunactie | Netherlands | `/zoeken?query=` | NL crowdfunding |
| KissKissBankBank | EU | `/projects/search?search=` | Creative + cause |
| Ulule | EU | `/search/?q=` | Reward + social |
| Catarse | Brazil | `/explore?search=` | Largest BR crowdfunding |
| Goteo | Spain | `/explore?query=` | Open source + social |
| Vakinha | Brazil | `/busca?q=` | BR “vaquinha” pots |
| Rally.org | US | Discover only | Political/social causes |
| Every.org | US | `/search?q=` | Nonprofit crypto-friendly |
| Open Collective | Global | **GraphQL API** | 600k+ accounts, no browser |

## Latency improvements (same release)

| Change | Before | After |
|--------|--------|-------|
| Browser launches per search | ~20 (one per platform) | **1 shared Chromium** |
| Per-URL page visits on search | Yes | **No** (link-only harvest) |
| Platform parallelization | API sequential, then browser | **All parallel** |
| Per-platform cap | 50 | **20** (configurable) |
| Global search timeout | 180s | **90s** |
| Per-platform timeout | none | **22s** |
| DB persist | Blocks response | **Background** |
| Repeat query | Full rescrape | **5 min cache** |

## Next batch (research only — not wired yet)

| Platform | Why backlog |
|----------|-------------|
| Raisely | JSON API may exist for public campaigns |
| Wonderful.org | UK — need search URL validation |
| Localgiving | UK community — sitemap |
| Neighbourly | UK corporate — weak public index |
| Anedot / WinRed | Political — different UX |
| Tiltify | Gaming charity streams |
| GoFundMe Charity | charity.gofundme.com subdomain |
| Facebook / Instagram | Blocked — no public API |

See `SCRAPER_PLATFORM_MATRIX.md` for the full ~150 list.

## Verify

```bash
cd scraper
python live_search.py --q "cancer" --json --limit 15
```

Expect `by_platform` keys for GoFundMe + multiple browser platforms within ~30s locally.
