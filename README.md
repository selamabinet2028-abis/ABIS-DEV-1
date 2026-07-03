# ABIS — Automated Biometric Identification System

Full-stack platform for the Ethiopian Federal Police Commission: multi-modal
biometric enrollment (fingerprint, palmprint, face), matching & identification,
forensic latent investigation, watchlists, police clearance certificates with
QR verification, appointments, payments, reporting, and administration.

**Stack:** React 18 + TypeScript + Vite · Django 5 + DRF · PostgreSQL 16 ·
Celery + Redis · Django Channels · Docker.

## Repository map
- `.ai/` — AI agent knowledge layer (memory, plans, contracts, task queue). **Read first.**
- `CLAUDE.md` / `.clinerules` — agent operating rules.
- `MASTER_PROMPT.md` — end-to-end build prompt for the AI coding agent.
- `backend/` — Django project (`config/` + `apps/` one app per ABIS module).
- `frontend/` — React SPA (feature-sliced).
- `ABIS-AI/` — local RAG assistant (ChromaDB + Ollama) over the codebase + .ai docs.
- `docs/` — SRS/SAD exports, manuals.

## Quickstart (Windows 11, PowerShell)
```powershell
git clone <repo> ABIS; cd ABIS
powershell -File scripts\setup.ps1     # venv, deps, docker db+redis, migrate, seed
powershell -File scripts\dev.ps1       # API :8000, Celery, Vite :5173
```
Demo logins after seeding: admin / operator / investigator / supervisor / auditor
(passwords printed by `seed_demo`).

## Status
Greenfield. Implementation proceeds via `.ai/TASK_QUEUE.md` (T-001 → T-022).
