# TEST_STRATEGY.md — ABIS Testing

## Current Testing Status (greenfield)
Unit: none · Integration: none · E2E: none. Everything below is the plan and
becomes the acceptance gate for tasks in TASK_QUEUE.md.

## Tooling
- Backend: **pytest + pytest-django + factory_boy + pytest-cov**; API tests via
  DRF APIClient. Celery tasks run eagerly in tests (`CELERY_TASK_ALWAYS_EAGER`).
- Frontend: **Vitest + React Testing Library + MSW** (mocked API).
- E2E (Phase 5, optional if time-boxed): Playwright happy paths.

## Critical workflows that MUST have tests
1. Auth: login, refresh rotation, logout blacklist, RBAC deny-by-default per role.
2. Enrollment: multipart biometric upload → quality score → record + encrypted template.
3. Dedup on enrollment complete → MatchJob → candidates; duplicate person flagged.
4. Latent workflow: upload → enhance ops → minutiae → LT-TP search → hit decision.
5. Watchlist alert fires on match against watchlisted person (WebSocket/consumer test).
6. Clearance: application → payment webhook (sandbox) → approval → certificate PDF
   with valid QR → public verification returns valid; tampered number returns invalid.
7. Audit: every mutation on Person/BiometricRecord/Certificate writes AuditLog;
   AuditLog is append-only (update/delete raise).
8. Reports: KPI endpoint role-scoping; XLSX/PDF export produces a readable file.

## Conventions
- Test files mirror app structure: `apps/<app>/tests/test_*.py`.
- Factories for every model; `seed_demo` reuses factories.
- Coverage gate: `pytest --cov=apps --cov-fail-under=80` on accounts, audit,
  enrollment, matching, clearance, verification.
- Frontend: each feature ships at least render + interaction tests for its main page.

## Security testing
- Tests asserting: unauthenticated 401s, wrong-role 403s, IDOR checks on
  person/case/certificate detail endpoints, upload type/size validation,
  webhook signature validation (sandbox secret).
