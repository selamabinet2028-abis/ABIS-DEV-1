from django.conf import settings
from django.db import models

from common.models import BaseModel


class Payment(BaseModel):
    """A clearance-fee payment. Amount is always computed server-side."""

    class Method(models.TextChoices):
        TELEBIRR = "telebirr", "Telebirr"
        CBE_BIRR = "cbe_birr", "CBE Birr"
        CHAPA = "chapa", "Chapa"
        CASH = "cash", "Cash (front desk)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(
        "registration.ClearanceApplication",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="ETB")
    method = models.CharField(max_length=10, choices=Method.choices)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    gateway_ref = models.CharField(max_length=64, blank=True, db_index=True)
    receipt_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_webhook = models.JSONField(default=dict, blank=True)  # last gateway payload
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="initiated_payments",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.method} {self.amount} {self.currency} ({self.status})"


class ReconciliationBatch(BaseModel):
    """Persisted result of a reconciliation run (DATABASE_DESIGN)."""

    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    totals = models.JSONField(default=dict)
    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_batches",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "reconciliation batches"

    def __str__(self) -> str:
        return f"Reconciliation {self.date_from or 'begin'}–{self.date_to or 'now'}"
