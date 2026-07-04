# DECISIONS.md — Engineering Decision Log (ADR)

## ADR-001
Date: 2026-07-03 · Decision: React 18 + TS + Vite SPA frontend
Context: Web app with rich, role-specific workflows (enrollment wizard, latent editor, dashboards).
Options: Next.js SSR, Django templates + HTMX, React SPA.
Chosen: React SPA. Reason: internal LAN system — no SEO need; richest ecosystem for canvas/image tooling; team skill.
Future impact: Public verification portal is part of the SPA with public routes; keep it lightweight.

## ADR-002
Date: 2026-07-03 · Decision: Django 5 modular monolith + DRF (one app per ABIS module)
Options: microservices, FastAPI, monolith.
Chosen: modular monolith. Reason: 20 tightly-related modules, single DB, small team, easiest ops for EFPC data center; service-oriented boundaries preserved at the app/service layer so future extraction is possible.

## ADR-003
Date: 2026-07-03 · Decision: PostgreSQL 16 as the only supported DB for biometric features
Reason: JSONB (minutiae, addresses), robust indexing, proven at 10M+ row scale.

## ADR-004
Date: 2026-07-03 · Decision: Pluggable MatchingEngine adapter; deterministic MockEngine in dev
Context: Real fingerprint/palm/face SDKs are proprietary and unavailable locally.
Chosen: `apps/matching/engines/base.py` interface (extract, identify, verify, dedup); engine selected via settings.
Future impact: Vendor SDK integration is a new engine class + contract tests; zero business-logic change.

## ADR-005
Date: 2026-07-03 · Decision: Celery + Redis for async; Channels + Redis for realtime
Reason: 1:N searches, dedup, exports are long-running; alerts need push. Windows dev uses `celery --pool=solo`.

## ADR-006
Date: 2026-07-03 · Decision: JWT auth — access in memory, refresh in httpOnly cookie
Reason: XSS-resistant token storage; SPA-friendly; blacklist on logout.

## ADR-007
Date: 2026-07-03 · Decision: All external integrations (SMS, payments, Fayda, CRIMS, etc.) behind sandbox-able connector drivers in `apimgmt`/provider apps, toggled by env
Reason: none reachable in local dev; keeps end-to-end flows testable.

## ADR-008
Date: 2026-07-03 · Decision: UUID PKs, insert-only AuditLog, encrypted template bytes
Reason: chain-of-custody, non-enumerable ids, legal admissibility requirements.

## ADR-009
Date: 2026-07-04 · Decision: Custom `accounts.User` defined at scaffold time (T-001), not T-004
Context: Django cannot swap `AUTH_USER_MODEL` after initial migrations without re-baselining the whole migration history; T-004 specifies a custom User.
Chosen: T-001 ships a minimal `User(AbstractUser)` with UUID pk (per ADR-008) and its `0001_initial` migration; T-004 extends it with role FK, org_unit, badge_number, phone, lockout/password fields via normal follow-up migrations.
Future impact: no migration re-baseline ever needed; all FKs to users are UUID from day one.

## ADR-010
Date: 2026-07-04 · Decision: Frontend scaffold library choices (T-002)
Context: Stack doc pins React 18 + Vite + Tailwind but not majors/patterns.
Chosen: Tailwind CSS **v4** (CSS-first via `@tailwindcss/vite`; there is NO tailwind.config.js — theme/customization live in `src/index.css`); React Router **v6** (`createBrowserRouter`); custom Zustand-based toast system (no third-party toast dep); MSW v2 for API mocking in Vitest.
Future impact: agents must not add a v3-style tailwind.config.js; nav/role gating lives in `src/components/layout/nav.ts`; all new features follow the `src/features/<module>` slice pattern from ARCHITECTURE.md.

## ADR-011
Date: 2026-07-04 · Decision: Dev Postgres publishes on host port **5433** (container 5432)
Context: The project workstation (and many dev machines) already runs a PostgreSQL on 5432; T-001 verification hit auth failures against the wrong server.
Chosen: docker-compose maps 5433:5432; `DATABASE_URL` default and `.env.example` use 5433. Prod compose (T-021) keeps Postgres internal-only (no host port), so this is dev-only.
Future impact: any tool connecting to dev Postgres must use 5433; never assume 5432 locally.

## ADR-012
Date: 2026-07-04 · Decision: PowerShell scripts are ASCII-only, saved UTF-8 **with BOM**, CRLF
Context: `powershell.exe` 5.1 parses BOM-less UTF-8 .ps1 as ANSI; em-dashes in strings broke the parser outright.
Chosen: scripts/*.ps1 use ASCII punctuation, UTF-8 BOM, `eol=crlf` via .gitattributes; shared helpers live in scripts/common.ps1 (dot-sourced).
Future impact: keep non-ASCII out of .ps1 files; new scripts dot-source common.ps1 for service startup/health-wait helpers.

## ADR-013
Date: 2026-07-04 · Decision: Auth contract reconciliation + lockout policy (T-004)
Context: API_DOCUMENTATION originally said login returns `{access, refresh, user}`; ADR-006 mandates refresh in an httpOnly cookie. The two conflicted.
Chosen: ADR-006 wins. Login → `{access, user}` + `abis_refresh` httpOnly cookie scoped to `/api/v1/auth/` (SameSite=Lax, Secure in prod); refresh rotates + blacklists (body `{refresh}` accepted as fallback for non-browser clients); logout 205. Lockout: 5 failures → 15 min lock (env-tunable), counter resets on lock/success. `DELETE /users/{id}` deactivates (is_active=False) + blacklists tokens — accounts are never hard-deleted (audit/chain-of-custody). Custom refresh view returns explicit 401 (DRF would map InvalidToken to 403 on authentication-free views).
Future impact: any new client must use cookie-based refresh; T-020 IDOR/security tests assert these exact semantics.

## ADR-014
Date: 2026-07-04 · Decision: Audit trail design (T-005)
Context: Golden rule #4 — audit every mutation of person/biometric data; DATABASE_DESIGN requires an INSERT-ONLY AuditLog.
Chosen: (1) Immutability enforced at the application layer — model save()-on-existing/delete() and queryset update()/delete() raise `AuditImmutabilityError`; a DB-level REVOKE is deferred to prod hardening (T-021) since dev connects as the table owner. (2) Tracking is registry-driven: `ABIS_AUDITED_MODELS` in settings lists `app.Model` labels; audit.apps.ready() connects generic pre_save/post_save/post_delete receivers — feature tasks just append their labels. (3) Actor/ip/user-agent come from a contextvar filled by `AuditContextMiddleware` (after AuthenticationMiddleware). (4) `ABIS_AUDIT_MASK_FIELDS` values are recorded as `***` (password); `ABIS_AUDIT_IGNORE_FIELDS` (last_login, updated_at) never trigger update rows. (5) Search auditing exposed via `audit.services.log_search` — wired into person/biometric endpoints from T-006 on.
Future impact: every new sensitive model MUST be added to ABIS_AUDITED_MODELS in the same task; T-020 adds tests asserting registry coverage; T-021 adds SQL REVOKE UPDATE/DELETE for defense in depth.

## ADR-015
Date: 2026-07-04 · Decision: Person card semantics (T-006)
Context: DATABASE_DESIGN requires unique person_no, JSONB addresses w/ GIN, soft delete for evidentiary retention.
Chosen: (1) `person_no` = `P-YYYY-NNNNNN` from a dedicated Postgres sequence (`abis_person_no_seq`, migration RunSQL) — concurrency-safe, never resets. (2) DELETE = soft delete (`is_deleted`), API queryset excludes deleted rows; hard deletes never happen. (3) Names use Ethiopian convention: first/middle (father)/last (grandfather), middle+last optional. (4) `national_id_no` (Fayda FIN) unique-nullable; serializers coerce '' → NULL. (5) Photo upload is a dedicated multipart action with extension whitelist + size cap + Pillow verification; files under `persons/photos/{person_id}/`. (6) Per-resource RBAC via `RoleMatrixPermission` (read vs write role sets) added to accounts.permissions.
Future impact: enrollment (T-007) links BiometricRecord → Person; dedup (T-008) flags duplicate persons rather than deleting; T-020 IDOR tests cover person detail routes.

## ADR-016
Date: 2026-07-04 · Decision: Biometric capture pipeline internals (T-007)
Context: No real capture SDK/NFIQ locally; templates must be encrypted at rest (ADR-008); MockEngine (T-008) needs comparable features.
Chosen: (1) Quality = contrast+Laplacian heuristic mapped to 1–5 (preprocessing.quality_score); production SDK replaces the function body, signature stays. (2) Template = `GRID16` (16×16 equalized grayscale, prefix `GRID16:`) — deterministic, similarity-comparable; engine/version recorded on BiometricTemplate. (3) Encryption via Fernet, key `ABIS_FIELD_KEY` env; dev default key ships in settings/.env.example, prod REQUIRES the env (fail fast) — rotate = re-encrypt job (future). (4) `template_bytes` added to audit mask list. (5) Rejected captures persist (accepted=false, no template) for operator feedback + stats. (6) Minimal `appointments.Station` created early (Enrollment FK), T-012 extends — same pattern as OrgUnit/ADR-009.
Future impact: T-008 MockEngine consumes GRID16 via decrypt; real SDK integration swaps preprocessing internals + engine class only.

## ADR-017
Date: 2026-07-04 · Decision: Matching pipeline shape (T-008)
Context: DEDUP probes a whole enrollment (up to 10 prints + palms + faces), but DATABASE_DESIGN's MatchJob had only single-probe FKs; LatentPrint doesn't exist until T-009.
Chosen: (1) MatchJob gains nullable `probe_enrollment` FK for DEDUP (DATABASE_DESIGN updated); `probe_latent` FK is added by T-009 additively. (2) Dedup aggregates person-level: best-scoring record per other person, probe person excluded; the presence of candidates IS the duplicate flag. (3) Engine interface = extract/similarity/verify/identify/dedup with identify/dedup implemented generically in the base class — SDK engines may override for native 1:N. (4) MockEngine similarity = 100·(1 − meanAbsDiff/255) over GRID16 vectors (identical → 100, distinct noise ≈ 66; default threshold 80, top-k 20 via env). (5) VERIFY-1_1 runs synchronously but still writes a done MatchJob row for the audit trail. (6) Celery dispatch is transaction.on_commit in real deployments, immediate in eager test mode. (7) Candidates are created row-by-row (not bulk) so audit signals fire.
Future impact: T-009 adds probe_latent + latent galleries (TP-LT/LT-*); T-011 hooks WatchlistAlert on DONE jobs with hits; contract tests gate any vendor engine.

## ADR-018
Date: 2026-07-04 · Decision: Latent workflow + candidate shape (T-009)
Context: LT-LT/TP-LT hits are other latents — identity unknown — but MatchCandidate required person+record; latent templates and enhancement interact.
Chosen: (1) MatchCandidate.person/record become nullable; new nullable `latent` FK; DB CheckConstraint requires record OR latent (DATABASE_DESIGN updated). (2) Latent templates are computed transiently at search time via engine.extract from the WORKING image (enhanced_image if present, else original) — never persisted, so no encryption-at-rest concern; destructive enhancement deliberately changes search results (tested). (3) `editor_history` JSONB records every enhance/minutiae action (who/when/ops/result sha256) for chain of custody. (4) case_no = CASE-YYYY-NNNNNN via PG sequence (same pattern as person_no). (5) Minutiae auto-extract is a deterministic cv2 corner stub; output schema {x,y,angle,type,quality} is the SDK contract. (6) EvidenceDocument.collected_by is free text (officers need not be system users). (7) spectacular ENUM_NAME_OVERRIDES added for cross-app enum name collisions (module-level choice aliases required — nested class paths don't import).
Future impact: T-010 pis face search reuses record-candidate path; T-011 watchlist alerts read candidates w/ person set; real extractor swaps stub internals only.

## ADR-019
Date: 2026-07-04 · Decision: Photo-probe FACE-1N searches (T-010)
Context: PIS searches start from an uploaded photo, not an enrolled record; the probe must survive for review + audit but is not an enrollment artifact.
Chosen: pis owns `PhotoProbe` (image, sha256, uploaded_by; audited); MatchJob gains a fourth nullable probe FK `probe_photo`. FACE-1N resolves its probe as photo-first, record-fallback; photo probes are extracted transiently at run time (like latents), never stored as templates. Upload is validated synchronously (extension/size + engine.extract decode check) so nothing persists on a bad upload. Candidate review reuses matching candidates + decision endpoint.
Future impact: T-019 seed uses PhotoProbe-free galleries (enrolled faces only); prod media hardening (T-021) must cover pis/probes/ paths.

## ADR-020
Date: 2026-07-04 · Decision: Watchlist alerting + WebSocket auth (T-011)
Context: Alerts must fire on job completion without matching importing watchlist; the SPA holds JWTs in memory, so ws needs its own auth path.
Chosen: (1) matching emits `match_job_completed` (django Signal, sent from execute_job after DONE); watchlist attaches in AppConfig.ready — dependency stays watchlist→matching. (2) Alerts fire per (active entry, job) for CANDIDATES (machine matches), not human hit-decisions — realtime warning is the point; dedup jobs alert too (watchlisted person re-enrolling under a new identity). Unique (entry, trigger_job) makes re-processing idempotent. (3) ws auth: `accounts.ws_auth.JWTAuthMiddleware` reads `?token=<access>`, loads user+role (role force-loaded so consumers never hit the DB); AlertConsumer gates on role in {admin, investigator, supervisor}, closes 4403 otherwise; group name "alerts". (4) Watchlists/entries deactivate, never hard-delete. (5) Consumer tests use URLRouter directly with scope-injected users + async_to_sync (no pytest-asyncio dependency, no threadpool DB visibility issues).
Future impact: T-018 frontend connects with the in-memory access token; alert fan-out per org-unit/severity can extend the group scheme later.

## ADR-021
Date: 2026-07-04 · Decision: Application status machine + booking model (T-012)
Context: Clearance flow spans registration/payments/enrollment/clearance tasks; public booking is ABIS's first anonymous surface.
Chosen: (1) Status transitions ONLY via registration.services.transition (explicit map; submitted_at stamped; decision_note on rejection); API serializers keep `status` read-only; submit requires an uploaded ID document. mark_paid is the T-013 webhook entry point. (2) TimeSlot = recurring daily window w/ per-date capacity; availability = capacity − booked(count, status=booked). Booking runs in a transaction with select_for_update on the slot (race-safe capacity), plus a conditional DB unique constraint (slot, date, phone, status=booked) — cancellation frees both. (3) Public endpoints: AllowAny + dedicated `public` throttle scope (30/min), limited serializer fields, no public listing of bookings; optional tracking_no links a booking to its application. (4) Appointment creation is public-only; staff PATCH manages statuses.
Future impact: T-013 flips submitted→paid; T-014 consumes in_review→approved→certificate_issued; T-018 public booking page; T-020 hardens public throttles.

## ADR-022
Date: 2026-07-04 · Decision: Payment gateway adapter + webhook security (T-013)
Context: No real gateways locally (golden rule: sandbox drivers); webhooks are unauthenticated HTTP from outside.
Chosen: (1) PaymentProvider ABC (create_checkout, parse_webhook, verify_signature) selected per method via `ABIS_PAYMENT_PROVIDERS`; SandboxProvider serves telebirr/cbe_birr/chapa in dev. (2) Webhook auth = HMAC-SHA256 over the RAW body, header `X-ABIS-Signature`, per-provider secrets from env, constant-time compare; signature is the only auth (AllowAny + `webhook` throttle scope). (3) Amounts are always computed server-side; webhook amount mismatch rejects. (4) Settlement (_settle) stamps paid_at + sequence receipt RCP-YYYY-NNNNNN and flips the application submitted→paid via registration.services.mark_paid; replays are idempotent (paid short-circuit). (5) Cash settles at initiate (front desk). (6) Reconciliation persists as ReconciliationBatch (totals + paid-but-application-not-paid mismatches).
Future impact: real gateway = new provider class + env swap; T-015 hooks SMS on paid; T-016 reports read ReconciliationBatch.

(Agents: append new ADRs below; never edit past entries.)
