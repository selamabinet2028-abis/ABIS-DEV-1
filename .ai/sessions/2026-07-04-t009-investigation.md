# Session 2026-07-04 — T-009 Investigation (Cases + Latents)

## What was done
- Models: `Case` (case_no CASE-YYYY-NNNNNN via PG sequence abis_case_no_seq,
  category FK, status open/closed/archived, lead_investigator),
  `LatentPrint` (case FK, modality finger|palm, image + enhanced_image,
  sha256, minutiae JSONB, editor_history JSONB, uploaded_by),
  `EvidenceDocument` (file, description, collected_by free text,
  collected_at, sha256 — chain of custody). All three audited.
- `investigation/services.py`: apply_operations (Pillow contrast/invert/
  rotate/crop w/ bounds check), enhance_latent (works on enhanced image if
  present; appends history {at, by, action, operations, result_sha256}),
  extract_minutiae (deterministic cv2 goodFeaturesToTrack stub → schema
  {x,y,angle,type,quality} — SDK contract), set_minutiae (manual replace +
  history), generate_case_no.
- Endpoints: cases CRUD (no delete) + /cases/{id}/latents/ (multipart) +
  /cases/{id}/evidence/ (GET/POST) + /cases/dashboard/ (aggregates incl.
  confirmed latent hits); latents read + /enhance/ + /minutiae/extract/ +
  PATCH /minutiae/ + /search/ (LT-TP|LT-LT → 202 job) + audited /image/ and
  /enhanced-image/. InvestigationPermission: read inv/sup/admin, write
  inv/admin.
- Matching extensions (T-008 deferrals closed): MatchJob.probe_latent FK;
  MatchCandidate person/record nullable + latent FK + CheckConstraint
  (record OR latent) — ADR-018; execute_job handles LT-TP (latent→records),
  LT-LT (latent→other latents), TP-LT (record→latent gallery); latent
  templates computed transiently from the WORKING image (enhanced wins);
  start_latent_search_job service; candidate serializer exposes latent +
  latent_case_no; IdentifyView LT-* message now points to /latents/{id}/search/.
- spectacular ENUM_NAME_OVERRIDES for modality/job_type collisions
  (module-level choice aliases: LATENT_MODALITY_CHOICES,
  MATCH_JOB_TYPE_CHOICES — nested class paths don't import_string).

## Verification (all green)
- pytest **206/206** (32 new), coverage **98%**, spectacular exit 0, style clean.
- **Full latent workflow (task verification)**: case → multipart latent
  upload (sha256, audit row) → enhance (history entry w/ operator + sha256)
  → minutiae auto-extract → manual PATCH → LT-TP search 202 → job done with
  suspect at rank 1 → decision hit w/ verified_by. ✔
- LT-LT: matching latent in another case found; candidate has latent set +
  person null. TP-LT: tenprint probe finds unsolved latent.
- Enhancement affects search: inverted latent no longer matches (proves
  working-image semantics). Threshold filtering; operator search 403;
  supervisor upload 403; evidence .exe rejected; crop out of bounds 400;
  minutiae schema validation; enhanced-image 404 before enhancement;
  dashboard aggregates.

## Next
- T-010 pis app (face photo search FACE-1N from an uploaded image +
  candidate review) — reuse enrollment face records gallery; upload probe
  is transient (extract → search, keep job trail).
