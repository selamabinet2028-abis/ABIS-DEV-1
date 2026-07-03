# ABIS — Automated Biometric Identification System

Full-stack platform for the Ethiopian Federal Police Commission: multi-modal
biometric enrollment (fingerprint, palmprint, face), matching & identification,
forensic latent investigation, watchlists, police clearance certificates with
QR verification, appointments, payments, reporting, and administration.

**Stack:** React 18 + TypeScript + Vite · Django 5 + DRF · PostgreSQL 16 ·
Celery + Redis · Django Channels · Docker.

## Repository map
- `.ai/` — AI agent knowledge layer (memory, plans, contracts, task queue). **Read first.**
- `CLAUDE.md` / `.clinerules` — agent operating rules.
- `MASTER_PROMPT.md` — end-to-end build prompt for the AI coding agent.
- `backend/` — Django project (`config/` + `apps/` one app per ABIS module).
- `frontend/` — React SPA (feature-sliced).
- `ABIS-AI/` — local RAG assistant (ChromaDB + Ollama) over the codebase + .ai docs.
- `docs/` — SRS/SAD exports, manuals.

## Quickstart — fresh clone (Windows 11, PowerShell)

Prerequisites: **Python 3.12** (via `py` launcher), **Node 20+**, **Docker Desktop** (running).

```powershell
git clone <repo> ABIS; cd ABIS
powershell -File scripts\setup.ps1     # venv, pip+npm deps, docker db+redis, .env, migrate, seed*
powershell -File scripts\dev.ps1       # API :8000, Celery worker, Vite :5173 (3 windows)
powershell -File scripts\test.ps1      # full gate: pytest, vitest, typecheck, lint, pip-audit, npm audit
```

What `setup.ps1` does, in order: check prerequisites → create `venv\` (Python
3.12) → `pip install` backend deps → `npm install` frontend deps → copy
`backend\.env.example` to `backend\.env` (if missing) → `docker compose up -d
db redis` and wait for healthchecks → `manage.py migrate` → `seed_demo`
(*skipped until T-019 delivers it). Idempotent — safe to re-run anytime.

Service endpoints:
| Service | Address | Notes |
|---|---|---|
| Django API | http://localhost:8000 | Swagger at `/api/docs/`, health at `/api/v1/health/` |
| Frontend | http://localhost:5173 | Vite proxies `/api` and `/ws` to :8000 |
| PostgreSQL 16 | localhost:**5433** | `abis`/`abis`, db `abis` — 5433 because 5432 is commonly taken |
| Redis 7 | localhost:6379 | Celery broker db 0, results db 1, Channels db 2 |

Demo logins after seeding (from T-019): admin / operator / investigator /
supervisor / auditor (passwords printed by `seed_demo`).

## Status
In build. Backend + frontend scaffolds and dev tooling are done (T-001..T-003);
implementation proceeds via `.ai/TASK_QUEUE.md` (T-004 → T-022).
