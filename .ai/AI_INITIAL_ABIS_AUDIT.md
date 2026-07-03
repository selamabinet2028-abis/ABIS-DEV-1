# AI_INITIAL_ABIS_AUDIT.md — Initial Project Audit

## Executive Summary
ABIS (Automated Biometric Identification System) for the Ethiopian Federal
Police Commission is at **greenfield** stage: proposal approved (software fee
ETB 80M + 15% VAT), requirements defined across 20 software modules, and the
`.ai/` knowledge layer fully authored. No application code exists. The plan is a
React 18 + Django 5 modular monolith on PostgreSQL with a pluggable biometric
matching adapter (mock engine locally, vendor SDK in production).

## Maturity Assessment
- Requirements: HIGH (proposal + module features enumerated)
- Architecture/design: HIGH (documented, ADRs recorded)
- Implementation: NONE (0%)
- Testing: NONE (strategy defined)
- Security: DESIGN-TIME (controls specified, risk register in place)
- Deployment: NONE (packaging plan in T-021)

## Biggest Risks
1. Proprietary matching/scanner SDKs absent in dev → mitigated via adapters/simulators (ADR-004, ADR-007).
2. Scope breadth (20 modules) vs. one-pass build → mitigated by strict TASK_QUEUE order and per-task verification.
3. Sensitive biometric data handling → non-negotiable controls in SECURITY_REVIEW.md from first migration.
4. Windows-local dev vs. Linux prod → docker-compose parity + PowerShell scripts.

## Recommended Development Sequence
Phase 0 foundation → identity/security spine → biometric pipeline → citizen
services → operations/integrations → hardening → deployment packaging
(see DEVELOPMENT_PLAN.md).

## First 10 Tasks AI Agents Should Execute
T-001 backend scaffold · T-002 frontend scaffold · T-003 Windows dev scripts ·
T-004 accounts/RBAC · T-005 audit · T-006 basedata · T-007 enrollment ·
T-008 matching engine · T-009 investigation · T-012 registration/appointments.
