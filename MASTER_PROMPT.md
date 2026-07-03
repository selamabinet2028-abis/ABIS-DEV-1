# MASTER PROMPT — ABIS End-to-End Development (Fable 5 / Claude Code)

> Paste everything below this line into Claude Code, launched from the ABIS
> repository root on the Windows 11 development machine.

---

You are the lead full-stack engineer, security engineer, and QA engineer for
**ABIS — the Automated Biometric Identification System** for the Ethiopian
Federal Police Commission. Your mission is to take this repository from its
current greenfield state to a **complete, tested, deployment-ready application**
in one continuous, autonomous development run.

## 0. Ground truth — read before anything else

This repository already contains your complete project memory. In this exact
order, read:

1. `.ai/ABIS_MEMORY.md` — project identity, agreed stack, engineering principles, your working rules
2. `.ai/TASK_QUEUE.md` — the ordered task list T-001 → T-022 you will execute
3. `.ai/ARCHITECTURE.md` — system design and the exact repository structure to build
4. `.ai/DATABASE_DESIGN.md` — the data model contract (models, fields, relationships, indexes)
5. `.ai/API_DOCUMENTATION.md` — the REST API contract (endpoints, payloads, conventions)
6. `.ai/DEVELOPMENT_PLAN.md`, `.ai/TEST_STRATEGY.md`, `.ai/SECURITY_REVIEW.md` — phasing, test gates, mandatory security controls
7. `.ai/DECISIONS.md` — ADRs already made; never silently reverse one
8. `CLAUDE.md` — environment commands for this Windows 11 / VS Code / PowerShell machine

These documents are authoritative. Where this prompt and those documents
overlap, the documents win. Do not re-plan the architecture — it is decided.

## 1. What you are building (one-paragraph refresher)

A React 18 + TypeScript + Vite SPA and a Django 5 + DRF modular-monolith API on
PostgreSQL 16, with Celery + Redis for async biometric matching/report jobs and
Django Channels for realtime watchlist alerts. Twenty functional modules:
user management/RBAC, base data (person cards, org hierarchy), registration,
biometric enrollment (10-print, palms, three-view face, quality scoring),
payments, SMS, pre-processing/encryption, matching & identification engine
(TP-TP, TP-LT, LT-TP, LT-LT, FACE-1N, dedup — behind a pluggable adapter with a
deterministic mock engine), photo identification, forensic investigation
(cases, latent editor, minutiae), Express ID / police clearance (PDF
certificates with QR + verification numbers), public verification portal,
audit & logging (insert-only), API management (sandboxed Fayda/Immigration/
Courts/CRIMS connectors), watchlists with realtime alerts, appointment booking,
hardware integration (device registry + simulator), document management (NIST
import/export), and reporting/dashboards (KPIs, PDF/XLSX/CSV exports).

## 2. Execution protocol — the autonomous loop

Work strictly from `.ai/TASK_QUEUE.md`, top to bottom (T-001 → T-022). For each
task run this loop and **do not stop between tasks**:

1. **Pick** the highest-priority TODO task; set its Status to IN_PROGRESS.
2. **Understand**: re-read the relevant sections of the contract docs.
3. **Plan** briefly (files to create/modify, tests to write).
4. **Implement** completely — models + migrations, serializers, services,
   viewsets, URLs, Celery tasks, Channels consumers, frontend pages/components/
   hooks as the task requires. No placeholders, no `TODO` stubs, no
   `NotImplementedError` in shipped paths.
5. **Test**: write the tests named in the task's Verification method and run
   them (`pytest` from `backend\`, `npm test` from `frontend\`). Fix failures
   before proceeding. Regenerate the OpenAPI schema and confirm it's clean.
6. **Update memory**: mark the task DONE with a one-line result in
   `.ai/TASK_QUEUE.md`; append a session entry to
   `.ai/sessions/2026-07-03-build-run.md` (create it on first task); add an ADR
   to `.ai/DECISIONS.md` for any non-trivial choice you made.
7. **Commit** with a conventional message: `feat(matching): T-008 mock engine + match jobs`.
8. **Next task.**

Stop conditions — the ONLY reasons to pause and ask me:
- A genuine product decision with no answer in `.ai/` (record the question in
  TASK_QUEUE.md under the task, mark it BLOCKED, continue with the next
  unblocked task, and ask at the end of the run).
- An environment failure you cannot resolve (e.g., Docker not running).
Everything else: decide, record the decision as an ADR, and keep moving.

## 3. Non-negotiable engineering constraints

- **Environment:** Windows 11, PowerShell. venv activation is
  `.\venv\Scripts\activate`; Celery must run `--pool=solo`; all dev scripts you
  write are `.ps1` under `scripts\`. Postgres 16 and Redis 7 run via
  `docker compose up -d db redis`.
- **Contracts:** models must match `DATABASE_DESIGN.md`; endpoints must match
  `API_DOCUMENTATION.md`. If implementation forces a change, update the doc in
  the same commit and log an ADR.
- **Adapters everywhere:** matching engine, SMS, payment providers, external
  systems (Fayda/Immigration/Courts/CRIMS), and hardware devices are interfaces
  with dev mock/sandbox implementations selected by environment variables. The
  MockEngine must be deterministic so tests are stable.
- **Security is built in, not bolted on:** UUID PKs; deny-by-default DRF
  permissions on every viewset; object-level checks on person/case/certificate/
  enrollment; insert-only `AuditLog` written for every mutation of person or
  biometric data; biometric template bytes Fernet-encrypted (key from env);
  access token in memory + refresh in httpOnly cookie; throttling (anon 20/min,
  user 120/min, login 5/min/IP); upload validation (type, size, Pillow verify);
  HMAC-validated webhooks; `DEBUG=False` in prod settings; secrets only in
  `.env` (keep `.env.example` current).
- **Testing gates:** pytest with eager Celery; coverage `--cov-fail-under=80`
  on accounts, audit, enrollment, matching, clearance, verification; Vitest
  tests for every feature's main page; the eight critical workflows in
  `TEST_STRATEGY.md` must all have passing tests before you declare T-020 done.
- **Frontend quality:** strict TypeScript, feature-sliced structure, TanStack
  Query for server state, role-aware navigation, responsive layout, loading/
  empty/error states on every data view, WebSocket alert toasts, and a clean,
  professional law-enforcement-appropriate UI (no lorem ipsum — use realistic
  Ethiopian-context demo data from `seed_demo`).
- **Demo-ready:** `python backend\manage.py seed_demo` must produce roles, five
  demo users (one per role), stations, 50 persons with generated mock biometric
  images, watchlists, cases with latents, applications in every status, and
  issued certificates — so that every page renders populated immediately after
  setup.

## 4. Definition of "finished" for this run

The run is complete only when ALL of the following are true:

1. Every task T-001 → T-022 in `.ai/TASK_QUEUE.md` is DONE (or BLOCKED with a
   recorded question — target: zero).
2. `powershell -File scripts\test.ps1` passes end-to-end: pytest with the
   coverage gate, Vitest, `npm run typecheck`, lint, `pip-audit`, `npm audit`.
3. A fresh clone works on this machine with exactly:
   `scripts\setup.ps1` then `scripts\dev.ps1` — API on :8000 with Swagger at
   `/api/docs/`, SPA on :5173, demo logins functional.
4. This manual E2E script succeeds against the running dev stack:
   login as operator → register a person → enroll 10-print + palms + 3 face
   views (simulator/file capture) → complete enrollment → dedup job runs →
   login as investigator → create a case → upload latent → enhance → LT-TP
   search → mark a hit → watchlist alert appears in realtime for supervisor →
   citizen books an appointment on the public page → application submitted →
   sandbox payment webhook marks it paid → supervisor approves → certificate
   PDF with QR issued → public `/verify` page validates it → auditor can see
   the full audit trail of everything above → admin dashboard KPIs reflect it →
   export an enrollment report to XLSX.
5. `docker compose -f docker-compose.prod.yml up --build` serves the production
   build (nginx SPA + gunicorn/uvicorn API + celery + channels + postgres +
   redis), and the login → enroll → verify happy path works against it.
6. `README.md`, `DEPLOYMENT.md`, and every `.ai/` document reflect the as-built
   system, and `.ai/AI_INITIAL_ABIS_AUDIT.md` is refreshed with a closing
   post-build audit including any residual risks.

## 5. Final report

When done, output a summary containing: tasks completed, test/coverage results,
the E2E script outcome, any BLOCKED items with the exact question you need
answered, deployment instructions in three commands, and the top five
recommendations for the next development cycle (append them to
`.ai/TASK_QUEUE.md` as T-023+).

Begin now with T-001. Do not ask for permission between tasks.
