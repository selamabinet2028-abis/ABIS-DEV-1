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
`POST /enrollments/` `{person, station?}` (operator auto-set) ·
`POST /enrollments/{id}/biometrics/` multipart `{modality, position, image}` →
quality check (NFIQ-like 1–5, threshold `ABIS_QUALITY_THRESHOLD`), returns
`{record_id, quality_score, accepted}`; accepted records get a
Fernet-encrypted template (`ABIS_FIELD_KEY`); rejected records persist with
`accepted=false` and no template. Modalities: finger (positions "1"–"10"),
palm (left/right), face (frontal/left_profile/right_profile) ·
`POST /enrollments/{id}/complete/` → `{status, dedup_job_id}` (job wired in
T-008; requires ≥1 accepted record) · `GET /biometric-records/{id}/image/`
(**access audited** as VIEW) · `GET /enrollments/` embeds records +
quality_summary. RBAC: read op/inv/sup/admin, write op/admin.

### matching
`POST /match/identify/` `{probe: record_id, job_type: TP-TP|TP-LT|FACE-1N,
threshold?}` → 202 `{job_id}` (LT-* probes arrive with T-009; DEDUP is
launched by enrollment completion only) ·
`POST /match/verify/` `{person_id, record_id}` → sync `{match, score, job_id}`
(a done VERIFY-1_1 job row is kept for the audit trail) ·
`GET /match/jobs/` `?status=&job_type=` · `GET /match/jobs/{id}/` → status +
ranked candidates (person-aggregated for DEDUP) ·
`POST /match/candidates/{id}/decision/` `{decision: hit|no_hit}`
(investigator/admin). RBAC: run/read = investigator/supervisor/admin.
Defaults: threshold 80, top-k 20 (`ABIS_MATCH_*` env); engine selected via
`MATCHING_ENGINE` setting (MockEngine in dev, ADR-004/017).

### pis
`POST /pis/search/` multipart `{image, threshold?, notes?}` → 202
`{job_id, probe_id}` (photo persisted as PhotoProbe w/ sha256 — ADR-019;
undecodable/oversize/bad-ext → 400, nothing persisted) ·
`GET /pis/jobs/{id}/` (FACE-1N only; includes probe_photo_detail) ·
`GET /pis/jobs/{id}/candidates/` → `{job_id, status, candidates[]}` ·
`GET /pis/probes/{id}/image/` (**audited**) · decisions via
`POST /match/candidates/{id}/decision/`. RBAC: inv/sup/admin.

### investigation
`CRUD /cases/` (no hard delete; `case_no` auto `CASE-YYYY-NNNNNN`) ·
`GET /cases/dashboard/` (aggregates: cases by status, latents, evidence,
confirmed latent hits) · `POST /cases/{id}/latents/` multipart
`{modality: finger|palm, image, notes?}` ·
`GET|POST /cases/{id}/evidence/` (chain of custody: collected_by,
collected_at, sha256 auto) · `GET /latents/` `?case=&modality=` ·
`POST /latents/{id}/enhance/` `{operations:[{op: contrast|invert|rotate|crop,
factor?|angle?|box?}]}` — applied to the working image, every call appended
to `editor_history` (who/when/ops/result sha256) ·
`POST /latents/{id}/minutiae/extract/` (deterministic stub; schema
{x,y,angle,type,quality}) · `PATCH /latents/{id}/minutiae/` (validated
replace) · `POST /latents/{id}/search/` `{job_type: LT-TP|LT-LT, threshold?}`
→ 202 `{job_id}` (searches use the ENHANCED image when present) ·
`GET /latents/{id}/image/` + `/enhanced-image/` (**audited**). RBAC: read
inv/sup/admin, write inv/admin. Latent-file hits appear as candidates with
`latent` set and `person: null` (ADR-018); TP-LT via /match/identify/ now
searches the latent gallery.

### watchlist
`CRUD /watchlists/` (DELETE → 405, deactivate via PATCH is_active) ·
`GET|POST /watchlists/{id}/entries/` (unique person per list) ·
`PATCH|DELETE /watchlists/{id}/entries/{entry_id}/` (DELETE deactivates) ·
`GET /watchlist-alerts/?acknowledged=false&entry__watchlist=&entry__severity=` ·
`POST /watchlist-alerts/{id}/ack/` (idempotent). Alerts fire automatically
when a DONE match job (identify/dedup/…) has a candidate on an active list —
one alert per (entry, job), score = best candidate score. WebSocket
`ws/alerts/?token=<access>` (JWT query-param auth — accounts.ws_auth) pushes
new alerts to admin/investigator/supervisor; others rejected (4403).
RBAC: inv/sup/admin.

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
