# Pledge.to API — nonprofit embedded checkout

**Status:** Research / pilot path for **nonprofit-only** campaigns (not personal GoFundMe).

## Why this matters for "one-click" value

[Pledge](https://www.pledge.to/products/apis) offers embeddable donation forms for **verified nonprofits** (EIN). That is the only compliant path to accept payment **without** sending the donor to a third-party tab — for a subset of campaigns.

## When GiveFund can use it

- Campaign classified as charity / nonprofit
- Resolvable **EIN** or Pledge organization ID
- Platforms: GlobalGiving, some Donorbox org pages, registered charities

## When not

- Personal medical, emergency, family GFM campaigns (majority of index)

## Pilot (future)

1. Sandbox API key from Pledge
2. `GET /campaigns/{id}/checkout` returns `mode: "pledge_embed" | "external"` 
3. Express Give page renders Pledge widget for eligible rows only

## Combined with Express Give (shipped)

Personal campaigns → **Express Give** (`give.html`) → deep `/donate` + email prefill + Link hints.  
Nonprofit campaigns → Pledge embed when integrated.
