import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModel


def id_document_path(instance: "ClearanceApplication", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return f"applications/{instance.id}/id-{uuid.uuid4().hex}.{ext}"


class ClearanceApplication(BaseModel):
    """Police clearance certificate application.

    Status transitions are enforced by registration.services.transition —
    the API never writes `status` directly (ADR-021).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PAID = "paid", "Paid"
        BIOMETRICS_CAPTURED = "biometrics_captured", "Biometrics captured"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CERTIFICATE_ISSUED = "certificate_issued", "Certificate issued"

    tracking_no = models.CharField(max_length=20, unique=True, editable=False)
    person = models.ForeignKey(
        "basedata.Person",
        on_delete=models.PROTECT,
        related_name="clearance_applications",
    )
    purpose = models.CharField(max_length=100)  # lookup category "purpose"
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.DRAFT
    )
    id_document = models.FileField(upload_to=id_document_path, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_applications",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.tracking_no} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.tracking_no:
            from .services import generate_tracking_no

            self.tracking_no = generate_tracking_no()
        return super().save(*args, **kwargs)
