# Session 2026-07-05 — T-015 Notifications (SMS)

## What was done
- Models: SmsTemplate (unique code, {placeholder} body, is_active; audited)
  + SmsMessage outbox (to_number, template SET_NULL, rendered body, status
  queued/sent/failed, provider_ref, sent_at, error, application FK;
  deliberately NOT audited — it is itself a log, ADR-024).
- Provider adapter: SmsProvider ABC + ConsoleSmsProvider (logs + fake ref),
  selected via ABIS_SMS_PROVIDER env (lru-cached import).
- Celery task notifications.send_sms: idempotent (sent short-circuit),
  provider failure → status failed + error, row retained.
- Trigger chain: registration.services.transition now emits
  `application_status_changed` (new registration/signals.py — old_status/
  new_status kwargs); notifications receiver maps submitted→
  application_submitted, paid→payment_received, certificate_issued→
  certificate_ready; context = name/tracking_no/receipt_no/verification_no
  (format_map w/ empty defaults). Skips quietly: no contact_phone, missing/
  inactive template, unmapped status (e.g. rejected).
- `ClearanceApplication.contact_phone` added (serializer-writable;
  DATABASE_DESIGN updated).
- Templates seeded via data migration (3 defaults).
- Endpoints: GET /sms/outbox/ (admin/supervisor; filters status/template,
  search incl. tracking_no), CRUD /sms/templates/ (admin write),
  POST /sms/send-test/ (admin). NotificationPermission read adm/sup,
  write adm.

## Verification (all green)
- pytest **342/342** (13 new, first-try), coverage 98%, spectacular exit 0,
  style clean.
- Task criterion: **status change enqueues SMS row** — submit → outbox row
  w/ template, tracking_no + name in body, SENT + console- ref (eager);
  paid via real HMAC webhook → payment_received w/ receipt_no; certificate
  issue → certificate_ready w/ verification_no. Skip paths: no phone,
  inactive template, rejection (unmapped). Endpoints: send-test admin 201 /
  supervisor 403; outbox filter + operator 403; seeded templates present;
  supervisor read-only on templates; anon 401.

## Next
- T-016 reports + dashboard: ReportDefinition/ReportRun, Celery export
  PDF/XLSX/CSV, role-scoped KPI endpoint, seed standard reports
  (enrollment stats, verification outcomes, case activity, duplicates,
  clearance issuance). openpyxl verification in tests.
