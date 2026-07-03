# MOBILE_STATUS.md — Mobile Biometric Application

## Status: PLANNED (not started; out of scope for the initial web MVP build)

Per the proposal, a companion mobile app supports field fingerprint capture and
on-the-spot identification with secure communication to central ABIS.

## Direction decision
- **Framework recommendation: React Native (Expo)** — reuses the team's React/TS
  skills, shares API client types with the web frontend.
- Alternative considered: Flutter (better camera/scanner plugin maturity in some
  vendors) — revisit when real handheld hardware SDKs are chosen.

## Enablers already in the web build (do these now)
- All capture/identify endpoints are plain REST + JWT → mobile-ready.
- `devices` app models `mobile_handheld` type; capture simulator supports
  file-based capture so mobile flows can be integration-tested server-side.
- Short-lived access tokens + refresh rotation already fit mobile security needs.

## Mobile backlog (future)
Field verify (fingerprint 1:1), field identify (1:N against wanted list subset),
offline queue with sync, device attestation + certificate pinning, secure storage
(Keystore/Keychain) for refresh tokens.

## Build/testing/release readiness: N/A until started.
