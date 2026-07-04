# ABIS_MEMORY.md — Persistent Project Memory

> Last updated: 2026-07-04 (T-001..T-010 DONE — through PIS face search)

## 1. ABIS Identity

- **Name:** ABIS — Automated Biometric Identification System
- **Client:** Ethiopian Federal Police Commission (EFPC)
- **Contractor:** Ethiopian Artificial Intelligence Institute (EAII)
- **Purpose:** Centralized, secure, scalable multi-modal biometric platform for
  criminal identification, forensic investigation, biometric enrollment, and
  police clearance certificate services.
- **Business goal:** Modernize Ethiopia's criminal identification infrastructure.
  Target capacity: 10M ten-print records, 10M dual palmprints, 2M unsolved latent
  fingerprints, 1.5M unsolved palm latents, 10M three-view facial images
  (frontal, left profile, right profile). 55 Biometric Enrollment Stations (BES),
  32 Biometric Investigation Workstations.
- **Standards:** ISO/IEC 19794, ANSI/NIST-ITL 1-2007 biometric data exchange.

## 2. Current Development State

**Status: FOUNDATION COMPLETE.** Backend + frontend scaffolds and the full
Windows dev toolchain (docker services, setup/dev/test scripts) verify green.
Feature modules begin at T-004.

- **Completed:** Project proposal, `.ai/` knowledge base, architecture, database
  design, API contract, development plan, task queue. **T-001** backend scaffold
  (Django 5.2.15 / Py 3.12 venv, 19 apps, settings split, Celery+Channels wired,
  health + schema + Swagger, custom `accounts.User` UUID pk — see ADR-009,
  pytest smoke green, git repo initialized on `main`). **T-002** frontend
  scaffold (Vite 6 + React 18 TS strict, Tailwind v4 CSS-first — ADR-010,
  axios client w/ single-flight refresh, Zustand auth store, role-aware shell,
  login page, toast system; Vitest 10/10, typecheck/lint/build clean).
  **T-003** dev tooling (docker-compose db@5433/redis@6379 — ADR-011,
  setup/dev/test.ps1 — ADR-012, README quickstart; full 6-gate test.ps1 PASS,
  live runserver + celery verified, Pillow CVE fix → 12.3).
  **T-004** accounts: RBAC classes (deny-by-default; reuse from
  `apps.accounts.permissions`), cookie-based JWT auth per ADR-013, lockout,
  UserActivityLog, users/roles CRUD, role/permission seed migration;
  63 tests, 98% cov; live login round-trip verified (also closes T-002 note).
  Shared abstract bases in `common/models.py` (UUIDModel/BaseModel) — use for
  every new model.
  **T-005** audit: insert-only AuditLog (guards raise AuditImmutabilityError),
  registry-driven tracking — **new sensitive models must be appended to
  `ABIS_AUDITED_MODELS` in settings** (ADR-014); actor context via
  AuditContextMiddleware; `/audit-logs/` admin+auditor read-only;
  `audit.services.log_search` ready for person/biometric search endpoints.
  Shared pytest fixtures live in `backend/conftest.py`.
  **T-006** basedata: Person (P-YYYY-NNNNNN sequence, soft delete, GIN
  addresses, Fayda FIN unique-nullable), OrgUnit/LookupValue/
  InvestigationCategory CRUD, validated photo upload, audited person search;
  `RoleMatrixPermission` for read/write role splits (ADR-015). 124 tests, 99%.
  **T-007** enrollment+preprocessing: Fernet-encrypted GRID16 templates
  (ABIS_FIELD_KEY; prod requires env — ADR-016), NFIQ-like quality 1–5 w/
  threshold rejection, NIST-ish metadata + sha256, audited image download,
  dedup stub at `enrollment.services.trigger_dedup` (T-008 replaces);
  minimal appointments.Station created early. 143 tests, 98%.
  **T-008** matching: MatchingEngine ABC + MockEngine (GRID16, threshold 80),
  MatchJob/MatchCandidate (+probe_enrollment for DEDUP — ADR-017), Celery
  run_match_job, identify/verify/jobs/decision endpoints, dedup wired into
  enrollment complete (duplicate person flagged @100). Engine contract tests
  gate future SDK engines. 174 tests, 98%. ws job push → T-011/T-018.
  **T-009** investigation: Case/LatentPrint/EvidenceDocument (chain of
  custody via editor_history + sha256), Pillow enhance ops, deterministic
  minutiae stub, LT-TP/LT-LT/TP-LT wired (latent candidates: nullable
  person/record + latent FK — ADR-018; latent templates transient from
  working image), case dashboard. Full latent workflow to hit decision
  green. 206 tests, 98%.
  **T-010** pis: PhotoProbe + MatchJob.probe_photo (ADR-019), photo-probe
  FACE-1N w/ sync decode validation, candidate review + audited probe image;
  face search from seeded faces green. 218 tests, 98%.
- **Partially completed:** None.
- **Unfinished:** T-011 onward in `TASK_QUEUE.md` — watchlist + Channels
  alerts, registration→certificates chain, reports, T-018 frontend,
  deployment.

## 3. Important Technologies (agreed stack)

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite, Tailwind CSS, React Router, TanStack Query, Zustand |
| Backend | Django 5 + Django REST Framework (DRF), Python 3.12 |
| Auth | JWT via `djangorestframework-simplejwt` (access+refresh, rotation, blacklist) |
| Database | PostgreSQL 16 (dev fallback: SQLite only for quick spikes, never for biometric features) |
| Async / jobs | Celery + Redis (matching jobs, report generation, SMS dispatch) |
| Realtime | Django Channels + Redis (watchlist alerts, matching-job status) |
| Matching engine | Pluggable adapter (`matching/engines/`); dev uses a deterministic mock engine; production SDK integrates behind the same interface |
| Files/media | Local `MEDIA_ROOT` in dev; S3-compatible object storage interface for prod |
| Reports | reportlab (PDF), openpyxl (Excel), csv; `qrcode` for certificate QR codes |
| Dev environment | Windows 11, VS Code, PowerShell; Python venv (`venv\Scripts\activate`); Node 20 LTS |
| Containerization | Docker + docker-compose for prod parity (optional in local dev) |

## 4. Known Problems / Open Risks

- Real biometric matching SDKs (fingerprint/palm/face) are proprietary and not
  available in local dev → **mock engine adapter is mandatory**; never hardcode
  a vendor SDK into business logic.
- Hardware devices (live scanners, signature pads, cameras) are absent in dev →
  Hardware Integration Module must expose a device-abstraction API with a
  **simulator mode** (file upload / webcam fallback).
- External systems (Fayda National ID, Immigration, Courts, CRIMS, SMS gateway,
  payment gateways) are unavailable locally → all integrations go through the
  API Management Module with **sandbox/stub drivers** toggled by env vars.
- Biometric data is highly sensitive → encryption at rest for templates/images,
  strict RBAC, full audit trail are non-negotiable from the first migration.

## 5. Important Engineering Principles

1. **Modular monolith** Django project: one app per ABIS module (see ARCHITECTURE.md).
   No cross-app imports of models except through documented service functions.
2. **API-first:** every feature lands as a versioned REST endpoint (`/api/v1/...`)
   matching `API_DOCUMENTATION.md` before UI work starts.
3. **RBAC everywhere:** every endpoint declares permissions; default is deny.
4. **Audit everything:** create/update/delete/search on person or biometric data
   writes an `AuditLog` row. No exceptions.
5. **Adapters for the outside world:** matching engines, devices, SMS, payments,
   external systems — all behind interfaces with mock implementations.
6. **Tests ship with code:** a task is not done until its tests pass (pytest +
   Vitest/React Testing Library). See TEST_STRATEGY.md.
7. **Windows-friendly dev:** all scripts must run in PowerShell; provide
   `Makefile`-equivalent `scripts/*.ps1` where needed.
8. **Conventional commits**, small PR-sized changes, migrations always committed.

## 6. AI Agent Instructions

- Start every session by reading this file and `TASK_QUEUE.md`.
- Work the highest-priority `TODO` task; set it `IN_PROGRESS`, implement, run
  tests, set it `DONE` with a one-line result note.
- After each task: append a session log in `.ai/sessions/YYYY-MM-DD-<topic>.md`
  and record any architectural choice in `DECISIONS.md`.
- Never invent endpoints, models, or fields that contradict
  `API_DOCUMENTATION.md` / `DATABASE_DESIGN.md`; if a change is needed, update
  those docs in the same commit and log the decision.
- Do not stop mid-task; stop only at task boundaries or blocking decisions,
  and record blockers in `TASK_QUEUE.md`.
