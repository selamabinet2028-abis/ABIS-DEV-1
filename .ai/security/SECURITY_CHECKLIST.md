# SECURITY_CHECKLIST.md — release gate (all boxes required before deployment)

## Authentication & session
- [ ] Argon2 hasher enabled; password validators (len>=12, complexity)
- [ ] Access 15m / refresh 12h rotation + blacklist verified by tests
- [ ] Lockout after 5 failed logins; admin unlock flow
- [ ] must_change_password on first login enforced

## Authorization
- [ ] Deny-by-default DRF permission on every viewset (grep audit)
- [ ] Object-level checks: person, case, certificate, enrollment (IDOR tests green)
- [ ] Role change restricted to admin and audited

## API
- [ ] Throttles: anon 20/min, user 120/min, login 5/min/IP
- [ ] Upload validation: content-type, size cap, Pillow verify, re-encode
- [ ] Webhook HMAC + idempotency
- [ ] DEBUG=False, generic error handler, ALLOWED_HOSTS set
- [ ] CORS restricted; security headers (CSP, X-Frame-Options, HSTS via nginx)

## Data
- [ ] Template bytes encrypted (test asserts ciphertext != plaintext)
- [ ] Media outside webroot; hashed filenames; SHA-256 recorded
- [ ] AuditLog insert-only enforced + covered by tests
- [ ] Backup + restore procedure documented and rehearsed

## Dependencies
- [ ] pip-audit clean or waivers documented
- [ ] npm audit (prod deps) clean or waivers documented
