# API_DOCUMENTATION.md — ABIS REST API Contract (v1)

**Base URL:** `/api/v1/` · **Format:** JSON · **Schema:** auto-generated OpenAPI at
`/api/schema/` + Swagger UI at `/api/docs/` (drf-spectacular).

## Authentication (as built in T-004 — see ADR-006/ADR-013)

- `POST /api/v1/auth/login/` `{username, password}` → `{access, user}` **+
  httpOnly refresh cookie** `abis_refresh` (path `/api/v1/auth/`, SameSite=Lax,
  Secure outside DEBUG). The refresh token is never in the response body.
  Lockout: 5 failed attempts → account locked 15 min → 403 with detail
  (thresholds via `ABIS_LOCKOUT_*` env). Scoped throttle `auth: 10/min`.
- `POST /api/v1/auth/refresh/` (cookie; `{refresh}` body fallback for
  API clients) → `{access}` + rotated refresh cookie; old token blacklisted;
  invalid/blacklisted → 401 `{detail, code: token_not_valid}`.
- `POST /api/v1/auth/logout/` → 205; blacklists refresh, clears cookie.
- `POST /api/v1/auth/password/change/` `{current_password, new_password}` →
  200; validates policy, blacklists all outstanding refresh tokens, clears
  cookie (re-login required).
- Header: `Authorization: Bearer <access>` — required on everything except
  the public verification and appointment-booking endpoints.
- Machine-to-machine (institutions): `X-API-Key` handled by `apimgmt`.
- Every auth event writes a `UserActivityLog` row (login_success/failed/
  blocked, account_locked, logout, password_change).

## Conventions

- Pagination: `?page=&page_size=` → `{count, next, previous, results}`
- Filtering/search/order: django-filter + `?search=` + `?ordering=`
- Errors: `{"detail": str}` or DRF field-error maps; error codes 400/401/403/404/409/422
- Async jobs return `202 {"job_id": uuid}`; poll `GET .../jobs/{id}/` or subscribe
  to WebSocket `ws/jobs/{id}/`.

## Endpoints by module (summary — keep in sync with code)

### accounts
`GET|POST /users/` · `GET|PATCH|DELETE /users/{id}/` (**DELETE deactivates**,
accounts are never hard-deleted; outstanding tokens blacklisted) ·
`CRUD /roles/` (delete → 409 while users assigned) · `GET /permissions/` ·
`GET /users/me/` (any authenticated) · `GET /users/{id}/activity/`
(admin + auditor read-only). All admin-gated unless noted; RBAC classes:
IsAdmin / IsOperator / IsInvestigator / IsSupervisor / IsAuditorReadOnly
(admin passes every gate).

### basedata
`CRUD /persons/` (search by name, person_no, national_id — **searches are
audited**; DELETE soft-deletes; `person_no` auto-generated `P-YYYY-NNNNNN`) ·
`POST /persons/{id}/photo/` multipart `{photo}` (jpg/png, ≤ ABIS_MAX_UPLOAD_MB,
Pillow-verified) · `CRUD /org-units/` · `CRUD /lookups/` (`?category=`) ·
`CRUD /investigation-categories/`. RBAC: persons read =
operator/investigator/supervisor/admin, persons write = operator/admin;
other base data read = any staff role, write = admin.

### registration & clearance
`POST /applications/` → creates tracking_no ·
`GET /applications/?status=&search=` · `GET|PATCH /applications/{id}/` ·
`POST /applications/{id}/submit/` · `POST /applications/{id}/decision/`
(`{decision: approved|rejected, note}`) ·
`POST /applications/{id}/issue-certificate/` → generates PDF + QR ·
`GET /certificates/{id}/download/`

### verification (PUBLIC)
`GET /public/verify/{verification_no}/` → `{valid, holder_name_masked, issued_at, expires_at, status}` ·
`POST /public/verify/qr/` `{qr_payload}` · Institutional: `POST /verify/api/` (API key, full detail)

### appointments (public booking + staff admin)
`GET /public/stations/` · `GET /public/stations/{id}/slots/?date=` ·
`POST /public/appointments/` · staff: `CRUD /appointments/`, `CRUD /stations/`

### payments
`POST /payments/initiate/` `{application_id, method}` → `{payment_id, checkout_ref}` ·
`POST /payments/webhook/{provider}/` (sandbox simulator in dev) ·
`GET /payments/?status=` · `POST /payments/reconcile/`

### enrollment
`POST /enrollments/` `{person_id, station_id}` ·
`POST /enrollments/{id}/biometrics/` multipart `{modality, position, image}` →
runs quality check, returns `{record_id, quality_score, accepted}` ·
`POST /enrollments/{id}/complete/` → triggers DEDUP MatchJob ·
`GET /biometric-records/{id}/image/`

### matching
`POST /match/identify/` `{probe: record_id|latent_id, job_type, threshold}` → 202 job ·
`POST /match/verify/` `{person_id, record_id}` → sync `{match: bool, score}` ·
`GET /match/jobs/{id}/` → status + candidates ·
`POST /match/candidates/{id}/decision/` `{decision: hit|no_hit}`

### pis
`POST /pis/search/` multipart face image → 202 FACE-1N job ·
`GET /pis/jobs/{id}/candidates/`

### investigation
`CRUD /cases/` · `POST /cases/{id}/latents/` multipart ·
`POST /latents/{id}/enhance/` `{operations:[...]}` (contrast, invert, rotate, crop) ·
`POST /latents/{id}/minutiae/extract/` · `PATCH /latents/{id}/minutiae/` ·
`POST /latents/{id}/search/` `{job_type: LT-TP|LT-LT}` · `CRUD /cases/{id}/evidence/`

### watchlist
`CRUD /watchlists/` · `CRUD /watchlists/{id}/entries/` ·
`GET /watchlist-alerts/?acknowledged=false` · `POST /watchlist-alerts/{id}/ack/` ·
WebSocket `ws/alerts/` pushes new alerts to supervisors/investigators.

### audit
`GET /audit-logs/?entity=&entity_id=&actor=&action=&date_from=&date_to=`
(auditor/admin only, read-only; `?search=` over entity_repr/actor/entity_id;
`entity` is `app_label.ModelName`, dates are ISO-8601). Rows are written
automatically for every mutation of models in `ABIS_AUDITED_MODELS`
(settings); sensitive fields masked (`***`), `last_login`/`updated_at`
noise skipped. AuditLog itself is insert-only — update/delete raise
(ADR-014).

### apimgmt
`CRUD /external-systems/` · `POST /external-systems/{id}/test/` ·
`CRUD /api-credentials/` · `GET /integration-logs/`

### notifications
`GET /sms/outbox/` · `POST /sms/send-test/` · templates CRUD (admin)

### devices
`CRUD /devices/` · `POST /devices/{id}/capture/` (simulator returns sample image in dev) ·
`GET /devices/{id}/status/`

### documents
`POST /documents/` multipart · `GET /documents/{id}/download/` ·
`POST /documents/nist/export/` `{person_id}` → NIST-style package ·
`POST /documents/nist/import/`

### reports
`GET /reports/definitions/` · `POST /reports/run/` `{definition_id, params, format}` → 202 ·
`GET /reports/runs/{id}/download/` ·
`GET /dashboard/kpis/` → enrollments today/week, pending applications, running
match jobs, hit rate, certificates issued, alerts open (role-scoped)

## Error handling

Standard DRF exceptions + custom `ABISError(code, detail)`; all 5xx paths log to
Sentry-compatible logger and write an AuditLog `system_error` row when they touch
person/biometric entities.
