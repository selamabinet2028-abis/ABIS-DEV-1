# API_AUDIT.md
Status: PENDING — run after T-014/T-020.
Scope: every /api/v1 endpoint — auth required?, throttle class, input validation,
object-level permission, error exposure, public endpoints enumeration resistance.
Method: generate endpoint inventory from drf-spectacular schema; check each row.
Output: findings table appended below.
