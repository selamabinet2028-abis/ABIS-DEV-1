# SECURITY_REVIEW.md — ABIS Security Posture (design-time review)

Greenfield: this documents the mandatory controls and the risk register the
implementation must satisfy. Re-audit after Phase 2 and Phase 5.

## Authentication
- JWT (SimpleJWT): access 15 min, refresh 12 h with rotation + blacklist on logout.
- Password policy: min 12 chars, complexity validators, `must_change_password`
  on first login, expiry every 90 days, Argon2 hasher.
- Account lockout after 5 failed attempts (UserActivityLog-driven), unlock by admin.
- MFA: design hook present (TOTP field on User); implement in hardening phase.

## Authorization
- RBAC deny-by-default. Roles: admin, operator, investigator, supervisor, auditor.
- Object-level checks: operators see own station's enrollments; investigators see
  assigned cases; auditors read-only everywhere.
- Privilege escalation guard: only admin can change roles; role changes audited.

## API Security
- Input validation via DRF serializers everywhere; file uploads restricted by
  content-type + size + image verification (Pillow verify).
- Rate limiting: DRF throttling — anon 20/min (public verify/booking), user 120/min,
  login 5/min/IP.
- Error exposure: DEBUG off in prod settings; generic 500 handler; no stack traces.
- Injection: ORM-only data access; no raw SQL without parameterization + review.
- Webhooks: HMAC signature check with per-provider secret.
- CORS locked to frontend origin; CSRF for session-authenticated admin only.

## Database Security
- Sensitive data: biometric templates encrypted at rest (Fernet, key in env);
  images stored outside webroot with hashed filenames; SHA-256 recorded for
  chain of custody.
- Least-privilege DB user; TLS to Postgres in prod; automated backups (NAS per
  proposal) with restore test documented.

## Frontend Security
- Tokens: access token in memory (Zustand), refresh in httpOnly cookie
  (SameSite=Strict) — never localStorage for refresh.
- XSS: React default escaping; no dangerouslySetInnerHTML; CSP header from nginx.
- Sensitive data: mask person identifiers in public verification responses.

## Mobile Security (future)
Certificate pinning, secure storage, device attestation — see MOBILE_STATUS.md.

## Dependency Security
- `pip-audit` and `npm audit` in test script; pin versions in requirements.txt;
  monthly review task in TASK_QUEUE.

## Security Risk Table

| Risk | Severity | Location | Recommendation |
|---|---|---|---|
| Biometric template theft | Critical | matching/enrollment storage | Encrypt at rest, key mgmt via env/HSM, access audited |
| IDOR on person/case/certificate | High | all detail endpoints | Object-level permission tests (mandatory) |
| Public verify endpoint scraping | Med | verification | Throttle, masked payloads, no enumeration (404 == invalid) |
| Payment webhook spoofing | High | payments | HMAC validation + idempotency keys |
| Audit log tampering | High | audit | Insert-only model; DB REVOKE UPDATE/DELETE; periodic hash chaining (Phase 5) |
| File upload abuse | Med | enrollment/documents | Type/size checks, image re-encode, AV hook point |
| Celery task data leakage | Med | matching/reports | No PII in task args beyond ids; results in DB not broker |
| Windows dev secrets in repo | Med | repo | .env only, .env.example committed, gitignore enforced |
