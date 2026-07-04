# TASK_QUEUE.md — ABIS Executable Task Queue

Agents work top-down. Statuses: TODO / IN_PROGRESS / BLOCKED / DONE.
A task is DONE only when its verification passes. Update this file after every task.

---

Task ID: T-001
Description: Backend scaffold — Django 5 project `config` with settings split
  (base/dev/prod), DRF, SimpleJWT, drf-spectacular, django-filter, CORS, Celery
  app, Channels ASGI, Postgres config via env, health endpoint `GET /api/v1/health/`.
  Create all 19 apps under `backend/apps/` (empty models ok). requirements.txt,
  pytest.ini, .env.example, .gitignore.
Priority: High · Status: DONE — 2026-07-04: scaffold complete (Py 3.12.12 venv,
  Django 5.2.15, 19 apps, settings base/dev/test/prod, Celery+Channels wired,
  custom accounts.User w/ UUID pk + initial migration); `manage.py check` clean,
  `spectacular --validate --fail-on-warn` clean, pytest 4/4 green (health,
  schema, docs). Note: dev runserver needs the T-003 docker db; local port
  5432 is occupied by a non-project Postgres → T-003 must publish on 5433.
Files involved: backend/**
Expected result: `python manage.py check` clean; health returns 200; Swagger at /api/docs/.
Verification method: pytest smoke test for health endpoint.

Task ID: T-002
Description: Frontend scaffold — Vite React TS, Tailwind, React Router, axios
  client with JWT interceptor + refresh, TanStack Query, Zustand auth store,
  app shell (sidebar/topbar) with role-aware navigation, login page, protected
  route wrapper, toast system.
Priority: High · Status: DONE — 2026-07-04: Vite 6 + React 18 TS strict scaffold;
  Tailwind v4 (CSS-first, ADR-010), axios client w/ single-flight refresh +
  Bearer injection, Zustand auth store (access in memory per ADR-006), role-aware
  sidebar/topbar shell, login page, ProtectedRoute w/ silent bootstrap, custom
  toast system. Vitest 10/10 green (MSW), typecheck/lint/build clean, dev server
  serves :5173. Live login round-trip verified 2026-07-04 after T-004
  (login sets abis_refresh cookie; me/refresh/logout all green over HTTP).
Files involved: frontend/**
Expected result: `npm run dev` serves app; login against backend works end-to-end.
Verification method: Vitest tests for auth store + login form; manual round-trip.

Task ID: T-003
Description: Dev scripts for Windows 11 — scripts/setup.ps1 (venv, pip install,
  npm install, migrate, seed), scripts/dev.ps1 (start Postgres+Redis via docker
  compose, runserver, celery --pool=solo, vite), scripts/test.ps1 (pytest + vitest
  + pip-audit + npm audit). docker-compose.yml with postgres:16 and redis:7.
Priority: High · Status: DONE — 2026-07-04: docker-compose (db on host 5433 —
  ADR-011, redis 6379, healthchecks), scripts/common|setup|dev|test.ps1
  (ASCII + UTF-8 BOM for PS 5.1). Verified: setup.ps1 idempotent end-to-end,
  migrate applied to docker db, live runserver health+Swagger 200 (closes
  T-001 deferred check), celery worker ready on redis, test.ps1 all 6 gates
  PASS (incl. pip-audit after Pillow 11→12.3 vuln fix). README fresh-clone
  quickstart documented.
Verification method: fresh-clone dry run documented in README.

Task ID: T-004
Description: accounts app — custom User (UUID, role FK, org_unit, badge_number,
  lockout fields), Role/Permission seed, RBAC permission classes
  (IsAdmin, IsOperator, IsInvestigator, IsSupervisor, IsAuditorReadOnly),
  auth endpoints (login/refresh/logout/password-change), UserActivityLog +
  lockout after 5 failures, users/roles CRUD.
Priority: High · Status: DONE — 2026-07-04: full User model (role/org_unit FKs,
  badge, lockout fields), Role+Permission catalog seeded via data migration,
  5 RBAC classes (deny-by-default, admin passes all gates), cookie-based auth
  endpoints per ADR-013 (login/refresh-rotate/logout/password-change),
  UserActivityLog, users/roles/permissions CRUD (DELETE user = deactivate).
  pytest 63/63 green (RBAC matrix, lockout, rotation+blacklist), apps coverage
  98%, schema --fail-on-warn clean, live HTTP round-trip verified. Minimal
  basedata.OrgUnit created early for the FK (T-006 extends).
Verification method: pytest — RBAC deny-by-default matrix, lockout, token rotation.

Task ID: T-005
Description: audit app — insert-only AuditLog model (REVOKE-style guard in
  save/delete), signal/middleware capturing mutations on tracked models,
  read-only query endpoint for auditor/admin with filters.
Priority: High · Status: DONE — 2026-07-04: insert-only AuditLog (save/delete/
  queryset guards raise AuditImmutabilityError), registry-driven signal
  tracking via ABIS_AUDITED_MODELS + AuditContextMiddleware (actor/ip/UA),
  masked password + ignored noise fields, /audit-logs/ read-only endpoint
  (admin+auditor, entity/entity_id/actor/action/date filters). ADR-014.
  pytest 90/90 green, coverage 98%, schema clean. Feature tasks MUST append
  new sensitive models to ABIS_AUDITED_MODELS.
Verification method: pytest — mutation writes log; update/delete on AuditLog raises.

Task ID: T-006
Description: basedata app — Person (person cards), OrgUnit hierarchy, LookupValue,
  InvestigationCategory; CRUD + search (name/person_no/national_id); person photo upload.
Priority: High · Status: DONE — 2026-07-04: Person (P-YYYY-NNNNNN via PG
  sequence, soft delete, GIN addresses, unique-nullable Fayda FIN), OrgUnit
  hierarchy CRUD, LookupValue (category+code unique), InvestigationCategory;
  photo upload w/ whitelist+size+Pillow validation; person searches audited
  via log_search; all 4 models in ABIS_AUDITED_MODELS; RoleMatrixPermission
  added for read/write role splits (ADR-015). pytest 124/124, cov 99%,
  schema clean.
Verification method: pytest CRUD/search; audit rows created.

Task ID: T-007
Description: enrollment + preprocessing — Enrollment, BiometricRecord,
  BiometricTemplate (Fernet-encrypted bytes); multipart capture endpoint per
  modality/position; quality scoring (Pillow/OpenCV heuristic 1–5); NIST-ish
  metadata; reject below threshold; complete endpoint stub (dedup wired in T-008).
Priority: High · Status: TODO
Verification method: pytest — upload 10-print set, quality scores persisted,
  template encrypted (bytes differ from plaintext), low-quality rejected.

Task ID: T-008
Description: matching app — MatchingEngine base interface, deterministic
  MockEngine (feature hash similarity), MatchJob + MatchCandidate models,
  Celery tasks for TP-TP/TP-LT/LT-TP/LT-LT/FACE-1N/DEDUP, identify/verify/job
  endpoints, candidate decision endpoint; wire dedup into enrollment complete.
Priority: High · Status: TODO
Verification method: pytest (eager Celery) — dedup flags duplicate person;
  identify returns ranked candidates; engine contract tests pass on MockEngine.

Task ID: T-009
Description: investigation app — Case, LatentPrint, EvidenceDocument (chain of
  custody); latent upload; enhance operations endpoint (contrast/invert/rotate/
  crop via Pillow, history kept); minutiae auto-extract stub + manual edit;
  LT-TP / LT-LT search launch; case dashboards data.
Priority: High · Status: TODO
Verification method: pytest — full latent workflow to candidate decision.

Task ID: T-010
Description: pis app — face photo search endpoint (FACE-1N via engine), photo
  investigation candidate review endpoints.
Priority: High · Status: TODO
Verification method: pytest — face search returns candidates from seeded faces.

Task ID: T-011
Description: watchlist app — Watchlist/Entry/Alert models + CRUD; hook: any DONE
  match job with a hit against watchlisted person creates WatchlistAlert and
  pushes over Channels `ws/alerts/`; acknowledge endpoint.
Priority: Medium · Status: TODO
Verification method: pytest incl. Channels communicator test.

Task ID: T-012
Description: registration + appointments — ClearanceApplication with tracking_no
  generator + status machine; document scan upload; public Station/TimeSlot/
  Appointment booking endpoints with availability logic.
Priority: High · Status: TODO
Verification method: pytest — booking prevents double-booking; status transitions enforced.

Task ID: T-013
Description: payments — Payment model, provider driver interface with
  `SandboxProvider` (telebirr/cbe_birr/chapa stubs), initiate + HMAC-validated
  webhook + receipt number generation + reconciliation report.
Priority: High · Status: TODO
Verification method: pytest — webhook flips application to paid; bad signature 403.

Task ID: T-014
Description: clearance + verification — approval decision endpoint; certificate
  generation (reportlab PDF, QR via qrcode, verification_no); public verify
  endpoints (masked), institutional API-key verify; VerificationEvent logging.
Priority: High · Status: TODO
Verification method: pytest — issued cert verifies valid; unknown number invalid;
  PDF and QR payload parse correctly.

Task ID: T-015
Description: notifications — SmsMessage outbox, ConsoleSmsProvider (dev), status
  notification triggers (submitted/paid/ready), templates.
Priority: Medium · Status: TODO
Verification method: pytest — status change enqueues SMS row.

Task ID: T-016
Description: reports + dashboard — ReportDefinition/ReportRun, Celery export to
  PDF/XLSX/CSV, KPI endpoint (role-scoped), seed standard reports (enrollment
  stats, verification outcomes, case activity, duplicates, clearance issuance).
Priority: Medium · Status: TODO
Verification method: pytest — KPI shape per role; XLSX opens via openpyxl.

Task ID: T-017
Description: apimgmt + devices + documents — ExternalSystem connectors with
  sandbox drivers (fayda/immigration/courts/crims) + test endpoint + logs;
  ApiCredential hashed keys; Device registry with simulator capture; StoredDocument
  + NIST-style export/import package (zip of images + JSON manifest).
Priority: Medium · Status: TODO
Verification method: pytest — connector test round-trip; NIST export re-imports.

Task ID: T-018
Description: Frontend features — build pages per module: dashboard (KPIs, charts
  via recharts), persons, enrollment wizard (webcam/file capture, quality feedback),
  matching job monitor + candidate comparison view, cases + latent editor (canvas
  ops), watchlist + realtime alert toasts (WebSocket), applications kanban/status,
  appointments admin, payments, certificate issue/download, public verify page,
  public booking page, users/roles admin, audit log viewer, reports runner.
Priority: High · Status: TODO
Verification method: Vitest per feature main page; manual E2E per critical flow.

Task ID: T-019
Description: seed_demo management command — roles, admin/operator/investigator/
  supervisor/auditor users, 3 stations, lookups, 50 persons with mock biometrics
  (generated images), 2 watchlists, sample cases/latents, sample applications
  through each status, sample certificates.
Priority: High · Status: TODO
Verification method: fresh DB → seed → all list pages non-empty; demo logins work.

Task ID: T-020
Description: Quality & security hardening — coverage ≥80% on critical apps,
  throttling config, security headers, IDOR tests, pip-audit/npm audit clean,
  password policy validators, lockout verified.
Priority: High · Status: TODO
Verification method: scripts/test.ps1 fully green with coverage gate.

Task ID: T-021
Description: Deployment packaging — backend Dockerfile (gunicorn+uvicorn worker),
  frontend Dockerfile (build → nginx with CSP + SPA fallback + /api proxy),
  docker-compose.prod.yml (postgres, redis, backend, celery, channels, nginx),
  .env.example, collectstatic/media volumes, backup script, DEPLOYMENT.md.
Priority: High · Status: TODO
Verification method: `docker compose -f docker-compose.prod.yml up --build`
  serves app; login + one enrollment + one verify succeed against it.

Task ID: T-022
Description: Documentation finalization — root README (quickstart Windows +
  Docker), update all .ai/ docs to reflect as-built state, final session log,
  AI_INITIAL_ABIS_AUDIT.md refresh with post-build audit.
Priority: High · Status: TODO
Verification method: docs review; .ai/ memory matches code.
