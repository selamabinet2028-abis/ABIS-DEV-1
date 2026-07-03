# ARCHITECTURE.md — ABIS System Architecture

## System Overview (plain language)

ABIS is a web platform the Ethiopian Federal Police uses to enroll people's
biometrics (fingerprints, palmprints, facial photos), search those biometrics to
identify suspects or verify identities, manage forensic latent-print cases, and
issue police clearance certificates with QR-verified authenticity. Administrators
manage users, roles, watchlists, and integrations; supervisors monitor dashboards
and reports; the public can verify certificates on a portal.

It is a **React SPA** talking to a **Django REST API** over JWT-authenticated
HTTPS, with **PostgreSQL** for data, **Celery/Redis** for long-running biometric
matching and report jobs, and **Django Channels** for realtime alerts.

## Technology Stack

- **Languages:** TypeScript (frontend), Python 3.12 (backend), SQL
- **Frameworks:** React 18 + Vite, Django 5 + DRF, Celery, Django Channels
- **Databases:** PostgreSQL 16, Redis (broker/cache/channels)
- **Infrastructure:** Docker/docker-compose (prod parity), Nginx (prod), Gunicorn/Uvicorn
- **External services (adapter pattern, stubbed in dev):** Matching SDK, SMS
  gateway, payment gateways, Fayda National ID, Immigration, Courts, CRIMS

## Repository Structure

```
ABIS/
├── .ai/                  # AI knowledge layer (this folder) — agent memory
├── .clinerules           # Rules for Cline/Roo agents
├── CLAUDE.md             # Rules + commands for Claude Code (Fable 5)
├── MASTER_PROMPT.md      # End-to-end build prompt for the coding agent
├── backend/              # Django project
│   ├── config/           # settings/ (base, dev, prod), urls.py, asgi.py, celery.py
│   ├── apps/
│   │   ├── accounts/     # 1. User Management (users, roles, RBAC, activity logs)
│   │   ├── basedata/     # 2. Base Data (person cards, org hierarchy, categories)
│   │   ├── registration/ # 3. Registration (clearance applicants, tracking numbers)
│   │   ├── enrollment/   # 4. Biometric Enrollment (10-print, palms, face, quality)
│   │   ├── payments/     # 5. Payment & Fee Management
│   │   ├── notifications/# 6. SMS Integration (adapter + templates + outbox)
│   │   ├── preprocessing/# 7. Data Encryption & Pre-processing (NIST convert, enhance)
│   │   ├── matching/     # 8. Matching & Identification Engine (adapter, jobs, candidates)
│   │   ├── pis/          # 9. Photo Identification System (face search, photo invest.)
│   │   ├── investigation/# 10. Biometric Investigation (latents, cases, evidence)
│   │   ├── clearance/    # 11. Express ID / Police Clearance (certificates, QR)
│   │   ├── verification/ # 12. Verification & Validation (public portal API)
│   │   ├── audit/        # 13. Audit & Logging (AuditLog, middleware, signals)
│   │   ├── apimgmt/      # 14. API Management (external system connectors, keys)
│   │   ├── watchlist/    # 15. Watchlist Management (lists, entries, realtime alerts)
│   │   ├── appointments/ # 16. Appointment Booking (locations, slots, bookings)
│   │   ├── devices/      # 17. Hardware Integration (device registry, simulator mode)
│   │   ├── documents/    # 18/19. Document Management (evidence files, migration, backup)
│   │   └── reports/      # 20. Reporting & Dashboard (reports, exports, KPIs)
│   ├── requirements.txt / requirements-dev.txt
│   ├── manage.py
│   └── pytest.ini
├── frontend/             # React SPA
│   └── src/
│       ├── api/          # axios client, endpoint wrappers, auth interceptors
│       ├── auth/         # login, token refresh, role guards
│       ├── components/   # shared UI (tables, forms, layout, charts)
│       ├── features/     # one folder per module mirroring backend apps
│       ├── pages/        # route-level pages incl. public verification portal
│       ├── stores/       # Zustand stores
│       └── routes.tsx
├── docker-compose.yml    # postgres, redis, backend, celery worker, frontend
├── scripts/              # PowerShell dev scripts (setup.ps1, dev.ps1, test.ps1)
└── docs/                 # SRS/SAD exports, user manual drafts
```

## Component Architecture

- **Frontend:** feature-sliced React. Each feature owns its pages, components,
  api hooks (TanStack Query), and types. Role-aware routing: `admin`,
  `operator`, `investigator`, `supervisor`, `auditor` see different navigation.
  Public routes: `/verify` (certificate verification), `/appointments/book`.
- **Backend:** modular monolith. Each Django app exposes DRF viewsets under
  `/api/v1/<module>/`. Long jobs (1:N searches, dedup, exports) run in Celery;
  the API returns a job id, the client polls or subscribes via WebSocket.
- **Matching engine:** `apps/matching/engines/base.py` defines
  `MatchingEngine` (enroll_template, identify, verify, dedup). `MockEngine`
  implements deterministic similarity over stored feature hashes for dev/testing;
  a production SDK engine plugs in via `MATCHING_ENGINE` setting.
- **Service communication:** frontend ↔ backend REST/JSON + WebSocket; backend ↔
  external systems via `apimgmt` connectors (HTTP, signed, sandboxed in dev).

## Data Flow

User action → React page → axios (JWT) → DRF viewset (permission check) →
service layer → PostgreSQL / Celery job → (matching engine adapter) →
AuditLog write → JSON response → TanStack Query cache → UI update.
Realtime: Celery/task events → Channels group → WebSocket → toast/alert in UI.

## Dependencies of note

- `djangorestframework-simplejwt` (auth), `drf-spectacular` (OpenAPI schema),
  `django-filter`, `celery`, `channels`, `channels-redis`, `psycopg[binary]`,
  `Pillow` + `opencv-python-headless` (image quality/pre-processing),
  `cryptography` (field encryption for templates), `reportlab`, `openpyxl`, `qrcode`.

## Architectural Risks

- Mock-vs-real matching engine drift → contract tests against the adapter interface.
- 20 modules invite coupling → enforce service-layer boundaries; no cross-app ORM writes.
- Large biometric blobs in Postgres → store files on disk/object storage; DB keeps
  metadata + encrypted template bytes only.
- Realtime + Celery + Windows dev → Celery runs with `--pool=solo` on Windows;
  document in scripts.
