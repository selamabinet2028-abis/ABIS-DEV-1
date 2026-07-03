# CLAUDE.md — Claude Code (Fable 5) instructions for ABIS

## What this project is
ABIS — Automated Biometric Identification System for the Ethiopian Federal
Police Commission. React 18 + TS (frontend/) · Django 5 + DRF (backend/) ·
PostgreSQL 16 · Celery/Redis · Channels. Full context: .ai/ (start with
ABIS_MEMORY.md, then TASK_QUEUE.md).

## Golden rules
- .ai/TASK_QUEUE.md is the single source of work. Execute tasks in order; a task
  is DONE only when its stated verification passes.
- .ai/API_DOCUMENTATION.md and .ai/DATABASE_DESIGN.md are contracts. Changing
  them requires updating the doc in the same commit + a new ADR in .ai/DECISIONS.md.
- Everything external is an adapter with a dev mock: matching engine, devices,
  SMS, payments, Fayda/Immigration/Courts/CRIMS.
- Security is non-negotiable: RBAC deny-by-default, insert-only AuditLog,
  encrypted biometric templates, throttling, upload validation.
- Update memory after every task: TASK_QUEUE status, session log in
  .ai/sessions/, ADRs when decisions are made.

## Environment (Windows 11, VS Code, PowerShell)
- Python 3.12 venv: `python -m venv venv; .\venv\Scripts\activate`
- Backend deps: `pip install -r backend\requirements.txt -r backend\requirements-dev.txt`
- Services: `docker compose up -d db redis`   (postgres:16, redis:7)
- Run API: `python backend\manage.py runserver`  (settings: config.settings.dev)
- Celery: `celery -A config worker -l info --pool=solo`  (from backend\)
- Frontend: `cd frontend; npm install; npm run dev`
- Migrations: `python backend\manage.py makemigrations && python backend\manage.py migrate`
- Seed demo: `python backend\manage.py seed_demo`

## Test / verify commands
- Backend: `pytest` (from backend\; eager Celery in tests), coverage:
  `pytest --cov=apps --cov-fail-under=80`
- Frontend: `npm test` (Vitest) · Type check: `npm run typecheck` · Lint: `npm run lint`
- Full gate: `powershell -File scripts\test.ps1`

## Code style
- Backend: black + isort + ruff; type hints on services; serializers validate all input.
- Frontend: eslint + prettier; strict TS; no `any` unless justified in a comment.
- Conventional commits, one commit per completed task minimum.

## Definition of Done (every task)
1. Code + migrations committed. 2. Tests written and green. 3. OpenAPI schema
regenerates cleanly. 4. .ai/ memory updated. 5. No new pip-audit/npm audit criticals.
