# Contributing

## Branching

Use **`main`** only. Do not create feature branches unless you have a specific reason.

Commit message prefixes:

- `[scraper]` — `/scraper`
- `[backend]` — `/backend`
- `[frontend]` — `/frontend`
- `[ops]` — deploy, CI, scripts
- `docs:` — README, HANDOFF, TASKS, etc.

## Workflow

1. Pull latest `main`
2. Make changes in the appropriate directory (see `AGENTS.md`)
3. Run tests: `cd backend && pytest tests/ -q`
4. Push to `main`
