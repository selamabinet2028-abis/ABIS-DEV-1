# Session 2026-07-05 — T-014 Clearance + Verification

## What was done
- `clearance.Certificate`: OneToOne application, denormalized person,
  CERT-YYYY-NNNNNN (abis_certificate_no_seq), RANDOM verification_no
  (EFP- + 12 hex, retry loop — non-enumerable per ADR-008), qr_payload,
  pdf_file, issued_by, expires_at (ABIS_CERT_VALIDITY_DAYS=180),
  status valid|revoked + `effective_status` property (expired computed).
- PDF: reportlab A4 (EFPC header, holder/person/tracking/cert/verify nos,
  dates, purpose, no-record statement) with embedded qrcode image.
- QR payload: compact JSON {v,no,name,issued,sig}; sig = first 16 hex of
  HMAC-SHA256(ABIS_QR_SECRET) over number|NAME|issued. **First test round
  caught that the name wasn't signed → forged names verified. Fixed.**
- Decision endpoint (in_review → approved|rejected + note; supervisor/
  admin) + thin advance endpoints /biometrics-captured/ + /to-review/
  (operator+; one legal step each — machine stays explicit).
- issue-certificate: approved-only, single-issue, transitions application
  to certificate_issued; audited PDF download; certificates read-only list.
- `verification.VerificationEvent` (channel portal|qr|api, result, ip,
  api_credential FK) — logged on EVERY attempt incl. unknown numbers.
- Public endpoints (`public` throttle): GET verify/{no}/ (masked name =
  first + initials; unknown → {valid:false,status:invalid} 200),
  POST verify/qr/ (signature check first; tampered → invalid; junk → 400).
  NOTE: qr/ route registered BEFORE the <verification_no> catch-all.
- Institutional POST /verify/api/ (X-API-Key `<prefix>.<secret>`, sha256
  hash + constant-time compare, `apikey` throttle scope) → full unmasked
  detail. Minimal `apimgmt.ApiCredential` + create/authenticate services
  (T-017 extends); key_hash added to audit mask.

## Verification (all green)
- pytest **329/329** (26 new), coverage 98%, spectacular exit 0 (renamed
  clearance DecisionSerializer → ApplicationDecisionSerializer to fix a
  cross-app component-name collision), style clean.
- Issued cert verifies valid (portal, masked) — task criterion ✔;
  unknown number invalid ✔; PDF starts %PDF >1kB ✔; QR payload parses,
  verifies, and breaks on name tamper ✔. Revoked/expired states; decision
  paths incl. RBAC (operator cannot decide, investigator cannot issue);
  advance-chain + illegal jump; reissue 400; audited download; API-key
  matrix (valid/wrong/inactive/missing); events logged w/ channel+ip+cred.

## Next
- T-015 notifications: SmsMessage outbox + ConsoleSmsProvider, triggers on
  submitted/paid/ready(certificate_issued) via registration transitions,
  templates. Hook into transition() or signals — prefer a signal from
  registration.services.transition to keep coupling clean.
