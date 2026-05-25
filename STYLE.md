# Style Guide

## Design System
Font: Inter + Instrument Serif (hero/stats), loaded from Google Fonts
Background: #F7F3ED
Card background: #FFFFFF
Card border: 1px solid #E8E2D9
Card border radius: 14px
Card shadow: 0 1px 4px rgba(28, 25, 23, 0.06)
Nav background: #FFFFFF
Nav border-bottom: 1px solid #E8E2D9
Footer background: #1C1917
Footer text: #A8A29E
Primary text: #1C1917
Secondary text: #78716C
Accent: #E8533A
Accent hover: #D44530
Border color: #E8E2D9

Progress bar:
  fill: #E8533A
  opacity: >75% funded = 1.0, >40% = 0.7, below = 0.45
  background: #E8E2D9
  height: 8px, border-radius: 4px

## UI Feel
Warm, human, trustworthy. This is about real people in real situations.
Cards should feel like stories, not product listings.
Generous whitespace. Nothing cramped.
Photos are 16:9 aspect ratio, object-fit cover, top of card.
Platform badge on cards: background #F7F3ED, border 1px solid #E8E2D9, text #78716C, 12px font.

## Button Style
Give Now button:
  background: #1C1917
  color: white
  border-radius: 8px
  padding: 12px 20px
  font-weight: 600
  hover: background #E8533A

Category pill (unselected):
  background: #EDE8E1
  color: #78716C
  border-radius: 999px
  padding: 8px 16px
  font-size: 14px

Category pill (selected):
  background: #1C1917
  color: #FFFFFF

## Typography
Hero serif headline: Instrument Serif italic, color #1C1917
Stats numbers: Instrument Serif, color #1C1917
Stats labels: #78716C, uppercase, letter-spacing 0.08em, 11px
Card title: #1C1917, font-weight 600
Card story snippet: #78716C
Nav links: #78716C, hover #1C1917

## Python Conventions
- Type hints on every function signature
- Pydantic models for all FastAPI request/response shapes
- All DB queries in db.py only, never inline in route handlers
- requirements.txt with pinned versions
- Use async/await throughout (aiosqlite is async)

## Scraper Conventions
- User agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
- Random delay between requests: 2-4 seconds (use random.uniform(2, 4))
- Wrap each campaign extraction in try/except -- log failures, continue scraping
- Never crash the whole run because one campaign failed to parse

## Git
- Commit prefix by agent: [scraper], [backend], [frontend]
- Never commit .env or givefund.db
- .gitignore must include: .env, givefund.db, __pycache__, .playwright
