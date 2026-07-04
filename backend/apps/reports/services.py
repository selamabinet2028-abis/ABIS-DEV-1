"""Report execution + role-scoped dashboard KPIs."""

from __future__ import annotations

import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.clearance.models import Certificate
from apps.enrollment.models import Enrollment
from apps.matching.models import MatchCandidate, MatchJob
from apps.registration.models import ClearanceApplication
from apps.verification.models import VerificationEvent
from apps.watchlist.models import WatchlistAlert

from .builders import BUILDERS
from .models import ReportRun
from .renderers import RENDERERS


def _dispatch(run: ReportRun) -> None:
    from .tasks import run_report

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        run_report.delay(str(run.id))
    else:
        transaction.on_commit(lambda: run_report.delay(str(run.id)))


def start_report_run(
    *, definition, params: dict, format: str, requested_by
) -> ReportRun:
    run = ReportRun.objects.create(
        definition=definition,
        format=format,
        params={**definition.default_params, **(params or {})},
        requested_by=requested_by,
    )
    _dispatch(run)
    return run


def execute_run(run: ReportRun) -> None:
    run.status = ReportRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])
    try:
        builder = BUILDERS[run.definition.query_key]
        payload = RENDERERS[run.format](builder(run.params))
    except Exception as exc:
        run.status = ReportRun.Status.FAILED
        run.error = str(exc)[:2000]
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        return
    run.file.save(
        f"{run.definition.code}.{run.format}", ContentFile(payload), save=False
    )
    run.status = ReportRun.Status.DONE
    run.finished_at = timezone.now()
    run.save()


# ------------------------------------------------------------- dashboard KPIs

# Which KPI blocks each role sees (task: role-scoped shape).
ROLE_BLOCKS = {
    Role.ADMIN: [
        "enrollments",
        "applications",
        "matching",
        "certificates",
        "alerts",
        "audit",
        "verification",
    ],
    Role.SUPERVISOR: [
        "enrollments",
        "applications",
        "matching",
        "certificates",
        "alerts",
        "audit",
        "verification",
    ],
    Role.OPERATOR: ["enrollments", "applications", "certificates"],
    Role.INVESTIGATOR: ["enrollments", "matching", "alerts"],
    Role.AUDITOR: ["audit", "verification"],
}

PENDING_STATUSES = [
    ClearanceApplication.Status.SUBMITTED,
    ClearanceApplication.Status.PAID,
    ClearanceApplication.Status.BIOMETRICS_CAPTURED,
    ClearanceApplication.Status.IN_REVIEW,
]


def _block_enrollments(today):
    week_start = today - datetime.timedelta(days=6)
    return {
        "today": Enrollment.objects.filter(created_at__date=today).count(),
        "week": Enrollment.objects.filter(created_at__date__gte=week_start).count(),
    }


def _block_applications(today):
    return {
        "pending": ClearanceApplication.objects.filter(
            status__in=PENDING_STATUSES
        ).count(),
        "submitted_today": ClearanceApplication.objects.filter(
            submitted_at__date=today
        ).count(),
    }


def _block_matching(today):
    decided = MatchCandidate.objects.exclude(
        decision=MatchCandidate.Decision.UNDECIDED
    ).count()
    hits = MatchCandidate.objects.filter(decision=MatchCandidate.Decision.HIT).count()
    return {
        "running_jobs": MatchJob.objects.filter(
            status__in=[MatchJob.Status.QUEUED, MatchJob.Status.RUNNING]
        ).count(),
        "jobs_today": MatchJob.objects.filter(created_at__date=today).count(),
        "hit_rate": round(hits / decided, 2) if decided else None,
    }


def _block_certificates(today):
    return {
        "issued_today": Certificate.objects.filter(created_at__date=today).count(),
        "issued_total": Certificate.objects.count(),
    }


def _block_alerts(today):
    return {"open": WatchlistAlert.objects.filter(acknowledged=False).count()}


def _block_audit(today):
    return {"events_today": AuditLog.objects.filter(at__date=today).count()}


def _block_verification(today):
    return {"today": VerificationEvent.objects.filter(created_at__date=today).count()}


_BLOCK_BUILDERS = {
    "enrollments": _block_enrollments,
    "applications": _block_applications,
    "matching": _block_matching,
    "certificates": _block_certificates,
    "alerts": _block_alerts,
    "audit": _block_audit,
    "verification": _block_verification,
}


def dashboard_kpis(role_name: str) -> dict:
    today = timezone.localdate()
    blocks = ROLE_BLOCKS.get(role_name, [])
    return {name: _BLOCK_BUILDERS[name](today) for name in blocks}
