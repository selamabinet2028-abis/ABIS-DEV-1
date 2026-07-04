"""Enrollment services: capture pipeline and completion."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.preprocessing import services as preprocessing
from apps.preprocessing.crypto import encrypt_bytes

from .models import BiometricRecord, BiometricTemplate, Enrollment


def capture_biometric(
    *,
    enrollment: Enrollment,
    modality: str,
    position: str,
    uploaded_file,
    user,
) -> BiometricRecord:
    """Quality-check, persist, and (if accepted) extract + encrypt a template."""
    image_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    score = preprocessing.quality_score(image_bytes)
    accepted = score >= settings.ABIS_QUALITY_THRESHOLD

    record = BiometricRecord.objects.create(
        enrollment=enrollment,
        person=enrollment.person,
        modality=modality,
        position=position,
        image=uploaded_file,
        sha256=preprocessing.sha256_hex(image_bytes),
        quality_score=score,
        accepted=accepted,
        nist_meta=preprocessing.build_nist_meta(
            image_bytes, modality=modality, position=position
        ),
        captured_by=user if (user and user.is_authenticated) else None,
    )

    if accepted:
        BiometricTemplate.objects.create(
            record=record,
            engine=preprocessing.TEMPLATE_ENGINE,
            version=preprocessing.TEMPLATE_VERSION,
            template_bytes=encrypt_bytes(preprocessing.extract_template(image_bytes)),
        )
    return record


def complete_enrollment(enrollment: Enrollment) -> dict:
    """Close the capture session. Dedup MatchJob is wired in T-008."""
    if enrollment.status != Enrollment.Status.IN_PROGRESS:
        raise ValidationError("Enrollment is not in progress.")
    if not enrollment.records.filter(accepted=True).exists():
        raise ValidationError("Enrollment has no accepted biometric records.")

    enrollment.status = Enrollment.Status.COMPLETED
    enrollment.completed_at = timezone.now()
    enrollment.save(update_fields=["status", "completed_at"])

    dedup_job_id = trigger_dedup(enrollment)
    return {"status": enrollment.status, "dedup_job_id": dedup_job_id}


def trigger_dedup(enrollment: Enrollment) -> str | None:
    """Stub until T-008: returns a MatchJob id once the matching app exists."""
    return None
