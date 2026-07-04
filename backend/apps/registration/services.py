"""Registration services: tracking numbers + application status machine."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from .models import ClearanceApplication

Status = ClearanceApplication.Status

# The only legal state moves (ADR-021). Terminal: rejected, certificate_issued.
TRANSITIONS: dict[str, set[str]] = {
    Status.DRAFT: {Status.SUBMITTED},
    Status.SUBMITTED: {Status.PAID},
    Status.PAID: {Status.BIOMETRICS_CAPTURED},
    Status.BIOMETRICS_CAPTURED: {Status.IN_REVIEW},
    Status.IN_REVIEW: {Status.APPROVED, Status.REJECTED},
    Status.APPROVED: {Status.CERTIFICATE_ISSUED},
    Status.REJECTED: set(),
    Status.CERTIFICATE_ISSUED: set(),
}


def generate_tracking_no() -> str:
    """Sequential tracking number, e.g. PCC-2026-000001 (PG sequence)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('abis_tracking_no_seq')")
        (value,) = cursor.fetchone()
    return f"PCC-{timezone.now().year}-{value:06d}"


def transition(
    application: ClearanceApplication, new_status: str, *, note: str = ""
) -> ClearanceApplication:
    allowed = TRANSITIONS.get(application.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Illegal status transition {application.status} → {new_status}."
        )
    old_status = application.status
    application.status = new_status
    update_fields = ["status"]
    if new_status == Status.SUBMITTED:
        application.submitted_at = timezone.now()
        update_fields.append("submitted_at")
    if note:
        application.decision_note = note
        update_fields.append("decision_note")
    application.save(update_fields=update_fields)

    from .signals import application_status_changed

    application_status_changed.send(
        sender=ClearanceApplication,
        application=application,
        old_status=old_status,
        new_status=new_status,
    )
    return application


def submit(application: ClearanceApplication) -> ClearanceApplication:
    if not application.id_document:
        raise ValidationError("A scanned ID document is required before submission.")
    return transition(application, Status.SUBMITTED)


def mark_paid(application: ClearanceApplication) -> ClearanceApplication:
    """Called by payments (T-013) on a confirmed webhook."""
    return transition(application, Status.PAID)
