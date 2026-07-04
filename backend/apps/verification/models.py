from django.db import models

from common.models import BaseModel


class VerificationEvent(BaseModel):
    """One verification attempt (public portal, QR scan, or institution API)."""

    class Channel(models.TextChoices):
        PORTAL = "portal", "Public portal"
        QR = "qr", "QR scan"
        API = "api", "Institutional API"

    class Result(models.TextChoices):
        VALID = "valid", "Valid"
        INVALID = "invalid", "Invalid"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    certificate = models.ForeignKey(
        "clearance.Certificate",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="verification_events",
    )
    verification_no_attempted = models.CharField(max_length=40)
    channel = models.CharField(max_length=8, choices=Channel.choices)
    result = models.CharField(max_length=8, choices=Result.choices)
    verifier_ip = models.GenericIPAddressField(null=True, blank=True)
    api_credential = models.ForeignKey(
        "apimgmt.ApiCredential",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verification_events",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["channel", "created_at"])]

    def __str__(self) -> str:
        return f"{self.channel} {self.verification_no_attempted} → {self.result}"
