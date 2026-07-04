import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModel


def biometric_image_path(instance: "BiometricRecord", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return (
        f"biometrics/{instance.person_id}/{instance.modality}/"
        f"{instance.position}-{uuid.uuid4().hex}.{ext}"
    )


class Modality(models.TextChoices):
    FINGER = "finger", "Fingerprint"
    PALM = "palm", "Palmprint"
    FACE = "face", "Face"


# NIST finger positions 1–10, palm left/right, face three-view.
MODALITY_POSITIONS: dict[str, set[str]] = {
    Modality.FINGER: {str(n) for n in range(1, 11)},
    Modality.PALM: {"left", "right"},
    Modality.FACE: {"frontal", "left_profile", "right_profile"},
}


class Enrollment(BaseModel):
    """A biometric capture session for one person at one station."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    person = models.ForeignKey(
        "basedata.Person", on_delete=models.PROTECT, related_name="enrollments"
    )
    station = models.ForeignKey(
        "appointments.Station",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.IN_PROGRESS
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Enrollment {self.id} for {self.person}"


class BiometricRecord(BaseModel):
    """One captured biometric image (chain of custody via sha256)."""

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="records"
    )
    person = models.ForeignKey(  # denormalized: direct biometric search paths
        "basedata.Person", on_delete=models.PROTECT, related_name="biometric_records"
    )
    modality = models.CharField(max_length=8, choices=Modality.choices)
    position = models.CharField(max_length=16)
    image = models.FileField(upload_to=biometric_image_path)
    sha256 = models.CharField(max_length=64)
    quality_score = models.PositiveSmallIntegerField()  # NFIQ-like 1–5
    accepted = models.BooleanField()
    nist_meta = models.JSONField(default=dict, blank=True)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="captured_records",
    )

    class Meta:
        ordering = ["modality", "position", "-created_at"]
        indexes = [
            models.Index(fields=["person", "modality"]),
            models.Index(fields=["enrollment", "modality", "position"]),
        ]

    def __str__(self) -> str:
        return f"{self.modality}/{self.position} of {self.person_id} (q={self.quality_score})"


class BiometricTemplate(BaseModel):
    """Encrypted feature template extracted from an accepted record.

    `template_bytes` holds Fernet ciphertext (ABIS_FIELD_KEY) — plaintext
    never touches the database (ADR-008).
    """

    record = models.OneToOneField(
        BiometricRecord, on_delete=models.CASCADE, related_name="template"
    )
    engine = models.CharField(max_length=32)
    version = models.PositiveSmallIntegerField(default=1)
    template_bytes = models.BinaryField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Template {self.engine} v{self.version} for record {self.record_id}"
