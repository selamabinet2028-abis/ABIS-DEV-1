# Session 2026-07-04 — T-001 Backend Scaffold

## What was done
- Created Python 3.12.12 venv at repo root (`venv/`) using the uv-managed
  CPython via `py -V:Astral/CPython3.12.12` (system Python is 3.13; project
  standard is 3.12).
- `backend/requirements.txt` + `requirements-dev.txt`; installed clean.
  Resolved: Django 5.2.15, DRF 3.16.x, SimpleJWT 5.5.x, drf-spectacular 0.28.x,
  celery 5.5.x, channels 4.x + channels-redis + daphne, psycopg[binary] 3.2,
  Pillow, opencv-headless, cryptography, reportlab, openpyxl, qrcode;
  dev: pytest 9.1.1, pytest-django 4.12, pytest-cov, factory_boy, black, isort,
  ruff, pip-audit.
- Django project `config` with settings split:
  - `base.py` — env-driven (django-environ, reads `backend/.env`), 19 local
    apps, DRF (deny-by-default `IsAuthenticated`, JWT auth, StandardPagination
    `?page_size=`, anon 60/min + user 600/min throttles), SimpleJWT
    (15 min access, 1 d refresh, rotation + blacklist), spectacular settings,
    Celery (redis /0 broker, /1 results), Channels (redis /2), TZ
    Africa/Addis_Ababa, Postgres via `DATABASE_URL`.
  - `dev.py` — DEBUG, browsable API + session auth, CORS for Vite :5173.
  - `test.py` — eager Celery, in-memory channel layer, MD5 hasher, no throttles.
  - `prod.py` — required env (fails fast), HSTS/secure-cookie/proxy-SSL baseline.
- Celery app (`config/celery.py`), Channels ASGI (`config/asgi.py`) with empty
  `config/routing.py` (consumers land in T-008/T-011).
- 19 apps created under `backend/apps/` per ARCHITECTURE.md.
- Minimal custom `accounts.User` (AbstractUser + UUID pk) + `0001_initial`
  migration — see ADR-009. Full fields land in T-004.
- `GET /api/v1/health/` (AllowAny, no DB) + `/api/schema/` + `/api/docs/`;
  admin at `/admin/`.
- `pytest.ini` (settings=config.settings.test, testpaths apps+tests),
  smoke tests `backend/tests/test_health.py`.
- Initialized git repo on `main`; root `.gitignore` + `.gitattributes`.

## Verification (all green)
- `manage.py check` — 0 issues.
- `manage.py spectacular --validate --fail-on-warn` — clean.
- `pytest -v` — 4/4 passed (health 200 + payload, no-auth access, schema 200,
  swagger UI 200). No DB required by these tests by design.

## Findings / notes for next tasks
- **Port 5432 is occupied on this machine** by a non-project PostgreSQL
  (password auth for user `abis` refused). T-003's docker-compose must publish
  Postgres on **5433** (and set `DATABASE_URL=postgres://abis:abis@localhost:5433/abis`
  in `.env.example`) or the conflict must be resolved.
- `manage.py runserver` (daphne) fails at boot without a reachable DB
  (`check_migrations` connects). Expected until T-003 provides the db service.
- Docker Desktop was not running; launched during session for T-003.
- pytest resolved to 9.x (pin was >=8.3) — no issues observed.

## Next
- T-002 Frontend scaffold (Vite React TS, auth store, login, app shell).
- T-003 dev scripts + docker-compose (remember port 5433 decision).
