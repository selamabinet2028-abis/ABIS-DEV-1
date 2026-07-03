# Session 2026-07-04 — T-002 Frontend Scaffold

## What was done
- `frontend/` scaffold written by hand (no create-vite; dir was non-empty):
  Vite 6 + React 18.3 + TS strict (project-references tsconfig), Tailwind v4
  CSS-first via `@tailwindcss/vite` (no tailwind.config.js — ADR-010),
  ESLint 9 flat config + typescript-eslint + react-hooks/react-refresh, Prettier.
- `src/api/client.ts` — axios instance, baseURL `/api/v1`, `withCredentials`
  (refresh cookie per ADR-006), request interceptor injects Bearer from auth
  store, response interceptor does **single-flight** token refresh on 401
  (auth URLs excluded), `apiErrorMessage()` DRF error extractor.
- `src/stores/auth.ts` — Zustand: user/accessToken/status; login/logout/
  bootstrap (silent restore via refresh cookie + `/users/me/`)/clearSession.
  Access token in memory only, never persisted.
- `src/stores/toast.ts` + `components/ui/Toaster.tsx` — custom toast system
  (success/error/info/warning, auto-dismiss 4 s, aria-live).
- Shell: `components/layout/` AppShell (sidebar + topbar + Outlet), Sidebar
  filters `nav.ts` NAV_ITEMS by role (admin/operator/investigator/supervisor/
  auditor), Topbar shows user + sign-out.
- `auth/ProtectedRoute.tsx` — bootstraps cold store, Loading state, redirect
  to /login with `from` state, optional `allowedRoles` gate.
- Pages: LoginPage (validation, DRF error display, redirects back to `from`),
  DashboardPage (KPI placeholders until T-016/T-018), ModulePlaceholderPage
  (all nav routes render it until T-018), NotFoundPage.
- `routes.tsx` — createBrowserRouter; placeholder routes generated from NAV_ITEMS.
- Vite dev proxy: `/api` → :8000, `/ws` → ws://:8000. Vitest (jsdom, globals,
  MSW v2 server in `src/test/`, store resets in setupTests).

## Verification (all green)
- `npm run typecheck` — clean (after adding missing `src/vite-env.d.ts`).
- `npm run lint` — clean.
- `npm test` — **10/10** (auth store: initial/login ok/login fail/logout-on-500/
  bootstrap ok/bootstrap fail; LoginPage: render/empty validation/bad creds
  server error/success navigates to dashboard).
- `npm run build` — clean (297 kB js, 14.5 kB css).
- `npm run dev` — serves on :5173 (HTTP 200 verified).

## Deferred / notes
- **Live login round-trip requires T-004** (backend auth endpoints don't exist
  yet). Contract assumed: login → `{access, user}` + httpOnly refresh cookie;
  refresh → `{access}` reading cookie; logout blacklists. T-004 MUST implement
  cookie-based refresh to match (ADR-006) — then manually verify the round-trip
  and update the T-002 queue note.
- React Router v6 emits v7 future-flag warnings in tests — informational only.

## Next
- T-003 dev scripts + docker-compose (Postgres on **5433** — host 5432 occupied).
