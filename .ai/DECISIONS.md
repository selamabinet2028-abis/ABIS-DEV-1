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

(Agents: append new ADRs below; never edit past entries.)
