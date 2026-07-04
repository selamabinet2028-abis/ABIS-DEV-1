import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import BaseModel


def certificate_pdf_path(instance: "Certificate", filename: str) -> str:
    return f"certificates/{instance.certificate_no}-{uuid.uuid4().hex[:8]}.pdf"


class Certificate(BaseModel):
    """Police clearance certificate (PDF + QR, publicly verifiable).

    `verification_no` is random (non-enumerable, ADR-008); `certificate_no`
    is the human-facing sequential number.
    """

    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        REVOKED = "revoked", "Revoked"

    application = models.OneToOneField(
        "registration.ClearanceApplication",
        on_delete=models.PROTECT,
        related_name="certificate",
    )
    person = models.ForeignKey(
        "basedata.Person", on_delete=models.PROTECT, related_name="certificates"
    )
    certificate_no = models.CharField(max_length=20, unique=True, editable=False)
    verification_no = models.CharField(max_length=20, unique=True, editable=False)
    qr_payload = models.TextField()
    pdf_file = models.FileField(upload_to=certificate_pdf_path, null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_certificates",
    )
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.VALID
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["verification_no"])]

    def __str__(self) -> str:
        return f"{self.certificate_no} ({self.effective_status})"

    @property
    def effective_status(self) -> str:
        if self.status == self.Status.REVOKED:
            return "revoked"
        if self.expires_at <= timezone.now():
            return "expired"
        return "valid"
