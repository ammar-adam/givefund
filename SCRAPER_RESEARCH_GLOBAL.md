# Global & Developing-Country Crowdfunding — Scraper Research

**Date:** May 2026  
**Purpose:** Close the discovery gap for donors outside US/UK-centric platforms (GoFundMe-only bias).

---

## Executive summary

| Tier | Platforms | Scraper status | Notes |
|------|-----------|----------------|-------|
| **A — Implemented** | LaunchGood, Islamic Relief CA, Ketto, M-Changa, BackaBuddy, Give.asia, Thundafund | Wired in `scraper/platforms/` | Discover scraper or dedicated module |
| **B — API / key** | GlobalGiving | `globalgiving.py` needs `GLOBALGIVING_API_KEY` | Official REST API, 10 projects/page |
| **C — Org appeals (not P2P index)** | Islamic Relief Worldwide, IRUSA iRaise | Not scraped as campaigns | Charity appeals, not peer fundraiser listings |
| **D — Blocked / hard** | PayPal Giving, Facebook fundraisers, WhatsApp collections | Skip | No public index, ToS risk |

---

## Islamic & humanitarian

### Islamic Relief Canada — Raise for Relief (`islamicrelief_ca`) ✅

- **URL:** https://fundraise.islamicreliefcanada.org/my/campaign/leaderboard  
- **Content:** 4,000+ peer fundraisers (mosques, Gaza appeals, community projects)  
- **Method:** Playwright leaderboard → `a[href*='/campaign/']`  
- **Legal:** Public leaderboard; rate-limit politely; no login bypass  
- **Donate friction:** Direct campaign URLs on same host  

### LaunchGood (`launchgood`) ✅ (existing)

- **Audience:** Global Muslim donors; strong in US, UK, MENA, South Asia  
- **Method:** Existing `launchgood.py` + `/v4/campaign/{slug}/donate` deep links  

### IRUSA iRaise — ⏸️

- **URL:** https://irusa.org/iraise/  
- **Gap:** Templates tied to IRUSA appeals; fewer independent peer pages than IRC leaderboard  
- **Next step:** Probe for public `/iraise/` listing API or sitemap  

### Islamic Relief Worldwide — ⏸️

- **URL:** https://islamic-relief.org/  
- **Gap:** Org-managed appeals (Palestine, Yemen), not a peer campaign index  
- **Use:** Link as charity context, not scrape as crowdfunding cards  

---

## South Asia

### Ketto (`ketto`) ✅

- **URL:** https://www.ketto.org/crowdfunding/fundraisers  
- **Audience:** India — medical emergencies dominate  
- **Method:** Discover scraper; markers `/fundraiser/`  
- **Risk:** Heavy JS; may need Playwright tuning / rate limits  

### Milaap — 📋 backlog

- **URL:** https://milaap.org/fundraisers  
- **Similar to Ketto** — add DiscoverConfig in next iteration  

### ImpactGuru — 📋 backlog

- **URL:** https://www.impactguru.com/explore  

---

## Africa

### M-Changa (`mchanga`) ✅

- **URL:** https://www.mchanga.africa/  
- **Stats (public):** 137k+ campaigns, Kenya-focused M-Pesa culture  
- **Method:** Discover scraper  

### BackaBuddy (`backabuddy`) ✅

- **URL:** https://www.backabuddy.co.za/  
- **Audience:** South Africa — medical, community, education  
- **Method:** Discover scraper  

### Thundafund (`thundafund`) ✅

- **URL:** https://www.thundafund.com/  
- **Audience:** South Africa rewards + social causes  
- **Method:** Discover scraper  

---

## Southeast Asia

### Give.asia (`giveasia`) ✅

- **URL:** https://give.asia/explore  
- **Audience:** Singapore, Malaysia, regional diaspora  
- **Method:** Discover scraper  

---

## Global development NGOs

### GlobalGiving (`globalgiving`) ✅ (API)

- **API:** https://www.globalgiving.org/api/  
- **Requires:** `GLOBALGIVING_API_KEY` (free registration)  
- **Yield:** Paginated active projects worldwide (10/page, `nextProjectId`)  
- **Without key:** Scraper returns 0 rows (logged warning)  

---

## Already in catalog (Western / global)

| Platform | Region | Scraper |
|----------|--------|---------|
| GoFundMe | US/EU/global | Algolia (`gofundme.py`) |
| JustGiving | UK | Discover |
| GoGetFunding | Global | Discover |
| Givebutter | US nonprofits | Discover |
| Chuffed | AU | Discover |
| Fundly → SignUpGenius | US | `fundly.py` (legacy) |

---

## Not recommended to scrape

| Source | Reason |
|--------|--------|
| WhatsApp / Telegram fundraisers | No public index |
| Facebook fundraisers | Graph API restricted; ToS |
| Local bank SMS “harambee” | No web listing |
| Zakat calculators / mosque PDFs | Not machine-readable campaigns |
| Aggressive HTML scrape of IR org donation forms | Compliance + duplicate appeals |

---

## Iteration log

| Round | Action | Result |
|-------|--------|--------|
| 1 | Desk research + platform matrix | This document |
| 2 | Implement IRC, Ketto, M-Changa, BackaBuddy, Give.asia, Thundafund | `extra.py` + `islamicrelief.py` |
| 3 | Wire registry, scrape loop, CI note | `__init__.py`, `scrape_loop.py` |
| 4 | Live probe (post-deploy) | Update yield table in `PRODUCTION.md` |

---

## Next research targets (round 4+)

1. **Milaap** + **ImpactGuru** (India)  
2. **WhyDonate** (EU/global)  
3. **GoFundMe UK** category pages (if separate from Algolia index)  
4. **CharityWater / UNHCR** campaign widgets — partner API only  
5. **IRUSA iRaise** public fundraiser directory if exposed  

---

*Re-run live probes quarterly; site HTML changes break discover scrapers.*
