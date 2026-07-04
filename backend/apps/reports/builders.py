"""Report dataset builders — one function per seeded definition.

Each builder takes params ({date_from, date_to} ISO strings, optional) and
returns ReportData(title, columns, rows, summary).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable

from django.db.models import Count, Sum

from apps.basedata.models import Person
from apps.clearance.models import Certificate
from apps.enrollment.models import BiometricRecord, Enrollment
from apps.investigation.models import Case, EvidenceDocument, LatentPrint
from apps.matching.models import MatchCandidate, MatchJob
from apps.payments.models import Payment
from apps.registration.models import ClearanceApplication
from apps.verification.models import VerificationEvent


@dataclass
class ReportData:
    title: str
    columns: list[str]
    rows: list[list]
    summary: dict = field(default_factory=dict)


def _parse_date(value) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def _range_filter(queryset, params, field_name: str = "created_at"):
    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__date__lte": date_to})
    return queryset


def enrollment_stats(params: dict) -> ReportData:
    enrollments = _range_filter(Enrollment.objects.all(), params)
    records = _range_filter(BiometricRecord.objects.all(), params)

    rows = [["Enrollments (total)", enrollments.count()]]
    for row in (
        enrollments.values("status").annotate(count=Count("id")).order_by("status")
    ):
        rows.append([f"Enrollments: {row['status']}", row["count"]])
    for row in (
        records.values("modality", "accepted")
        .annotate(count=Count("id"))
        .order_by("modality")
    ):
        accepted = "accepted" if row["accepted"] else "rejected"
        rows.append([f"Records: {row['modality']} ({accepted})", row["count"]])
    rows.append(["Persons on file", Person.objects.filter(is_deleted=False).count()])
    return ReportData("Enrollment Statistics", ["Metric", "Value"], rows)


def verification_outcomes(params: dict) -> ReportData:
    events = _range_filter(VerificationEvent.objects.all(), params)
    rows = [
        [row["channel"], row["result"], row["count"]]
        for row in events.values("channel", "result")
        .annotate(count=Count("id"))
        .order_by("channel", "result")
    ]
    return ReportData(
        "Verification Outcomes",
        ["Channel", "Result", "Count"],
        rows,
        summary={"total": events.count()},
    )


def case_activity(params: dict) -> ReportData:
    cases = _range_filter(Case.objects.all(), params)
    rows = [["Cases (total)", cases.count()]]
    for row in cases.values("status").annotate(count=Count("id")).order_by("status"):
        rows.append([f"Cases: {row['status']}", row["count"]])
    rows.append(
        ["Latents on file", _range_filter(LatentPrint.objects.all(), params).count()]
    )
    rows.append(
        [
            "Confirmed latent hits",
            MatchCandidate.objects.filter(
                decision=MatchCandidate.Decision.HIT, job__probe_latent__isnull=False
            ).count(),
        ]
    )
    rows.append(["Evidence documents", EvidenceDocument.objects.count()])
    return ReportData("Case Activity", ["Metric", "Value"], rows)


def duplicates(params: dict) -> ReportData:
    candidates = (
        MatchCandidate.objects.filter(
            job__job_type=MatchJob.JobType.DEDUP, person__isnull=False
        )
        .select_related("job__probe_enrollment__person", "person")
        .order_by("-job__created_at")[:500]
    )
    rows = [
        [
            str(candidate.job_id),
            (
                candidate.job.probe_enrollment.person.person_no
                if candidate.job.probe_enrollment
                else ""
            ),
            candidate.person.person_no,
            candidate.score,
            candidate.decision,
        ]
        for candidate in candidates
    ]
    return ReportData(
        "Potential Duplicate Persons",
        ["Job", "Enrolled person", "Matched person", "Score", "Decision"],
        rows,
        summary={"flagged": len(rows)},
    )


def clearance_issuance(params: dict) -> ReportData:
    applications = _range_filter(ClearanceApplication.objects.all(), params)
    rows = []
    for row in (
        applications.values("status").annotate(count=Count("id")).order_by("status")
    ):
        rows.append([f"Applications: {row['status']}", row["count"]])
    certificates = _range_filter(Certificate.objects.all(), params)
    rows.append(["Certificates issued", certificates.count()])
    paid = _range_filter(Payment.objects.filter(status=Payment.Status.PAID), params)
    rows.append(
        ["Fees collected (ETB)", str(paid.aggregate(t=Sum("amount"))["t"] or 0)]
    )
    return ReportData("Clearance Issuance", ["Metric", "Value"], rows)


BUILDERS: dict[str, Callable[[dict], ReportData]] = {
    "enrollment_stats": enrollment_stats,
    "verification_outcomes": verification_outcomes,
    "case_activity": case_activity,
    "duplicates": duplicates,
    "clearance_issuance": clearance_issuance,
}
