# Agent Boundaries

All work is merged to **`main`** only. Folder boundaries below are for organization, not separate git branches.

## Agent 1 -- Scraper
- Works exclusively in /scraper
- Owns: scraper/main.py, scraper/platforms/, scraper/db.py, scraper/requirements.txt
- Writes to givefund.db at repo root (path from DB_PATH env var)
- Does NOT read from the backend, does NOT touch /backend or /frontend
- Entry point: python main.py (optionally: python main.py --category medical)

## Agent 2 -- Backend
- Works exclusively in /backend
- Owns: backend/main.py, backend/db.py, backend/models.py, backend/requirements.txt
- Reads from givefund.db at repo root (path from DB_PATH env var), never writes
- Exposes REST API on PORT env var
- Does NOT touch /scraper or /frontend

## Agent 3 -- Frontend
- Works exclusively in /frontend
- Owns: frontend/index.html (single file, all CSS and JS inline or in same directory)
- Calls backend via API_URL config variable at top of index.html
- If backend is unreachable, fall back to hardcoded mock data matching the API contract in TASKS.md
- Does NOT touch /scraper or /backend

## Shared files -- READ ONLY for all agents, never modify
- CLAUDE.md
- AGENTS.md
- TASKS.md
- STYLE.md
- .env
- givefund.db (backend reads, scraper writes -- no other agent touches it)

## Conflict rules
- Each subdirectory has its own requirements.txt, there is no root requirements.txt
- No shared utility code across directories
- If you need to signal something to another agent, update TASKS.md under the Notes section only
- Never modify another agent's files even to fix a bug -- note it in TASKS.md instead
