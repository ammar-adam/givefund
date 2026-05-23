# Style Guide

## Design System
Font: Inter, loaded from https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap
Background: #FAFAFA
Card background: #FFFFFF
Card border radius: 16px
Card shadow: 0 2px 8px rgba(0,0,0,0.08)
Accent / CTA color: #E8533A
Primary text: #1A1A1A
Secondary text: #6B6B6B
Border color: #EEEEEE

Progress bar colors:
  >75% funded: #22C55E (green)
  >40% funded: #F59E0B (amber)
  <=40% funded: #EF4444 (red)
Progress bar background: #F0F0F0
Progress bar height: 8px, border-radius: 4px

## UI Feel
Warm, human, trustworthy. This is about real people in real situations.
Cards should feel like stories, not product listings.
Generous whitespace. Nothing cramped.
Photos are 16:9 aspect ratio, object-fit cover, top of card.
Platform badge: small pill top-right of photo, white background, #6B6B6B text, 12px font.

## Button Style
Give Now button:
  background: #E8533A
  color: white
  border-radius: 8px
  padding: 12px 20px
  font-weight: 600
  width: 100%
  cursor: pointer
  no border
  hover: background #D44530

Category pill (unselected):
  background: #F0F0F0
  color: #6B6B6B
  border-radius: 999px
  padding: 8px 16px
  font-size: 14px

Category pill (selected):
  background: #1A1A1A
  color: #FFFFFF

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
