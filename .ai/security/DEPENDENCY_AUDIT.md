# DEPENDENCY_AUDIT.md
Status: PENDING — run in T-020 and monthly thereafter.
Method: `pip-audit -r backend/requirements.txt` and `npm audit --omit=dev` in frontend/.
Record: date, tool output summary, CVEs, action taken (upgrade/waiver+reason).
