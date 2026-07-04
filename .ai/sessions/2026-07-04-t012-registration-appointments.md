# Session 2026-07-04 — T-012 Registration + Appointments

## What was done
- `registration.ClearanceApplication`: tracking_no PCC-YYYY-NNNNNN
  (abis_tracking_no_seq), 8 statuses, id_document upload path, submitted_at,
  decision_note, created_by. Status machine in services.TRANSITIONS —
  transition() validates the map, submit() requires an ID document,
  mark_paid() is T-013's webhook entry. API keeps `status` read-only.
- Endpoints: applications CRUD (no delete; search tracking_no + person
  names; filter status/purpose/person), POST /document/ (pdf/jpg/png +
  size cap), POST /submit/. ApplicationPermission op/sup/admin.
- `appointments.TimeSlot` (recurring daily window, capacity, unique station+
  window) + `Appointment` (status booked/cancelled/completed/no_show,
  full_name/phone, optional application link, conditional unique
  (slot,date,phone,status=booked)).
- Booking service: station/slot/date validation, transaction +
  select_for_update(slot) capacity check, duplicate-phone check —
  cancellation frees capacity. availability() annotates booked counts.
- PUBLIC endpoints (AllowAny, ScopedRateThrottle `public` 30/min, base +
  test rates added): GET /public/stations/ (active, limited fields),
  GET /public/stations/{id}/slots/?date= (past 400), POST
  /public/appointments/ (+tracking_no link, unknown → 400).
- Staff: stations CRUD + time-slots CRUD (admin write, window validation),
  appointments GET/PATCH only (creation is public-side).
- Audit registry += ClearanceApplication, TimeSlot, Appointment.

## Verification (all green)
- pytest **282/282** (40 new, first-try green), coverage 98%, spectacular
  exit 0, style clean.
- Status machine: full legal chain draft→…→certificate_issued; rejection
  path w/ note; 6 illegal jumps raise + state unchanged; PATCH cannot touch
  status; double submit 400; submit w/o document 400.
- Booking: anonymous booking 201; same phone/slot/date 400; capacity 2 →
  third booking 400; cancel frees seat (rebooking succeeds); past date 400;
  foreign-station slot 400; tracking link + unknown tracking 400;
  availability decrements after booking; inactive stations hidden publicly.
- RBAC: applications matrix (investigator/auditor 403), stations write
  admin-only, staff endpoints anon 401, public endpoints anon OK.

## Next
- T-013 payments: Payment model, provider driver interface + SandboxProvider
  (telebirr/cbe_birr/chapa), initiate + HMAC-validated webhook (bad sig 403)
  + receipt numbers + reconciliation report. Webhook flips application
  submitted→paid via registration.services.mark_paid (already in place).
