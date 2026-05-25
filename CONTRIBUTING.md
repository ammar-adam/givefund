# Contributing

## Branching

Use **`main`** only. Do not create feature branches unless you have a specific reason.

**One-time cleanup (if `agent1/scraper` still exists on GitHub):**  
Settings → General → Default branch → switch to **`main`** → Save. Then delete the old `agent1/scraper` branch under Branches.

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
