# .ai/ — ABIS AI Knowledge Layer ("AI Brain Folder")

This folder is the **persistent memory** of the ABIS project for AI coding agents
(Claude Code / Fable 5, Cline, Roo Code, Continue). Source code tells an agent
*what exists*. This folder tells an agent **why it exists, what is incomplete,
what decisions were made, and what must happen next**.

## Reading order for any new agent session

1. `ABIS_MEMORY.md` — project identity, current state, engineering principles
2. `TASK_QUEUE.md` — what to work on next (the single source of truth for work)
3. `ARCHITECTURE.md` — system design and repository structure
4. `DATABASE_DESIGN.md` and `API_DOCUMENTATION.md` — contracts you must respect
5. `DECISIONS.md` — do not silently reverse a recorded decision
6. `SECURITY_REVIEW.md` and `TEST_STRATEGY.md` — quality gates for every task

## File index

| File | Purpose |
|---|---|
| `ABIS_MEMORY.md` | Project identity, development state, known problems, agent instructions |
| `ARCHITECTURE.md` | System overview, tech stack, repo structure, data flow, risks |
| `DEVELOPMENT_PLAN.md` | Phased roadmap (Stabilization → Features → Quality → Production) |
| `TASK_QUEUE.md` | Ordered, executable tasks. Agents work from here |
| `SECURITY_REVIEW.md` | Security posture, risk table, mandatory controls |
| `TEST_STRATEGY.md` | Testing status, missing tests, testing plan |
| `DATABASE_DESIGN.md` | Schemas, models, relationships, migrations (Mermaid ERD) |
| `API_DOCUMENTATION.md` | Endpoints, request/response formats, auth, errors |
| `MOBILE_STATUS.md` | Mobile companion app status and direction |
| `DECISIONS.md` | Engineering decision log (ADR format) |
| `AI_INITIAL_ABIS_AUDIT.md` | Executive audit: maturity, risks, first 10 tasks |
| `sessions/` | Dated session logs — the engineering history of ABIS |
| `security/` | Security agent workspace: checklists and audits |

## Rules for agents

- **Update memory after every task.** Mark the task in `TASK_QUEUE.md`, append a
  session file in `sessions/`, and record any new decision in `DECISIONS.md`.
- **Never modify these files destructively.** Append and amend; do not delete history.
- **Blocked?** Write the blocker into `TASK_QUEUE.md` under the task, pick the next
  unblocked task, and continue.
