# DEVELOPMENT_PLAN.md — ABIS Roadmap (Greenfield)

Each task lists: **Priority** (High/Med/Low) · **Complexity** (S/M/L) ·
**Dependencies** · **Verification**. Executable breakdown lives in TASK_QUEUE.md.

## Phase 0 — Foundation (repo, tooling, skeletons)
- Scaffold backend (Django 5, settings split, DRF, JWT, spectacular, Celery,
  Channels, Postgres/Redis via docker-compose) — High · M · none ·
  `python manage.py check` + healthcheck endpoint returns 200.
- Scaffold frontend (Vite React TS, Tailwind, router, axios client, auth flow,
  layout shell with role-aware nav) — High · M · backend auth ·
  login → dashboard round-trip works.
- CI-ready scripts: `scripts/setup.ps1`, `dev.ps1`, `test.ps1` (Windows 11) —
  High · S · none · fresh clone to running app in ≤ 5 commands.

## Phase 1 — Core identity & security spine
- accounts (users, roles, RBAC, activity logs) — High · M · Phase 0 · pytest suite green.
- audit (insert-only AuditLog + middleware/signals) — High · M · accounts ·
  every person/biometric mutation produces a row (tested).
- basedata (persons, org units, lookups) — High · M · accounts · CRUD + search tests.

## Phase 2 — Biometric pipeline
- enrollment + preprocessing (capture API, quality scoring, encrypted templates) —
  High · L · basedata · upload 10-print set → records + quality scores persisted.
- matching engine adapter + MockEngine + MatchJob/candidates + Celery — High · L ·
  enrollment · DEDUP and TP-TP identify return ranked candidates deterministically.
- pis (face 1:N) and investigation (cases, latents, editor ops, LT searches) —
  High · L · matching · latent enhance → search → candidate decision flow tested.
- watchlist + realtime alerts (Channels) — Med · M · matching · hit on watchlisted
  person pushes WebSocket alert.

## Phase 3 — Citizen services
- registration + appointments (public booking) — High · M · basedata.
- payments (sandbox providers + webhook simulator + receipts) — High · M · registration.
- clearance certificates (PDF, QR, verification numbers) + public verification
  portal + institutional verify API — High · L · payments, matching.
- notifications/SMS outbox (console provider in dev) — Med · S · registration.

## Phase 4 — Operations & integration
- reports & dashboard (KPIs, PDF/XLSX/CSV exports, scheduled runs) — Med · M · all.
- apimgmt connectors (Fayda, Immigration, Courts, CRIMS — sandbox stubs) — Med · M.
- devices (registry + simulator capture) · documents (evidence, NIST import/export)
  — Med · M.

## Phase 5 — Quality & production readiness
- Test completion to ≥80% backend coverage on critical apps; frontend component
  tests for auth, enrollment, matching review, clearance — High · L.
- Security hardening pass per SECURITY_REVIEW.md checklist — High · M.
- Dockerfiles (backend, frontend/nginx), docker-compose.prod.yml, .env.example,
  gunicorn/uvicorn config, static/media strategy, backup script — High · M ·
  `docker compose -f docker-compose.prod.yml up` serves the app.
- docs: README quickstart, deployment guide, seed demo data — High · S.
