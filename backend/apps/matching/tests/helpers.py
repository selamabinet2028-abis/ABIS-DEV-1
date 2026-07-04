"""Test helpers: enroll persons with deterministic images."""

import io

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.basedata.tests.factories import PersonFactory
from apps.enrollment.models import Enrollment
from apps.enrollment.services import capture_biometric
from apps.enrollment.tests.factories import EnrollmentFactory


def png_bytes(seed: int) -> bytes:
    array = np.random.default_rng(seed).integers(0, 255, (128, 128), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(array, mode="L").save(buffer, format="PNG")
    return buffer.getvalue()


def upload(seed: int, name: str = "img.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, png_bytes(seed), content_type="image/png")


def enroll_person(
    seed: int, *, modality: str = "finger", position: str = "1", person=None
):
    """Create a completed-capture enrollment with one accepted record."""
    enrollment = EnrollmentFactory(person=person or PersonFactory())
    record = capture_biometric(
        enrollment=enrollment,
        modality=modality,
        position=position,
        uploaded_file=upload(seed),
        user=None,
    )
    assert record.accepted, "helper images must pass the quality threshold"
    return enrollment, record


def complete(enrollment: Enrollment) -> Enrollment:
    from apps.enrollment.services import complete_enrollment

    complete_enrollment(enrollment)
    enrollment.refresh_from_db()
    return enrollment
