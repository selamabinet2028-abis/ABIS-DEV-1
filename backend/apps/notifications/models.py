from django.db import models

from common.models import BaseModel


class SmsTemplate(BaseModel):
    """Message template with {placeholder} substitution."""

    code = models.CharField(max_length=64, unique=True)
    body = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class SmsMessage(BaseModel):
    """Outbox row — one SMS, dispatched asynchronously via the provider."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    to_number = models.CharField(max_length=32)
    template = models.ForeignKey(
        SmsTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.QUEUED
    )
    provider_ref = models.CharField(max_length=64, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=500, blank=True)
    application = models.ForeignKey(
        "registration.ClearanceApplication",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sms_messages",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"SMS to {self.to_number} ({self.status})"
