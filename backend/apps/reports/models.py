import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModel


def report_file_path(instance: "ReportRun", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"reports/{instance.definition.code}/{uuid.uuid4().hex}.{ext}"


class ReportDefinition(BaseModel):
    """A runnable report. `query_key` maps to a builder in reports.builders —
    definitions are seeded, not user-defined SQL."""

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    query_key = models.CharField(max_length=64)
    default_params = models.JSONField(default=dict, blank=True)
    scheduled = models.CharField(max_length=64, blank=True)  # cron expr (storage only)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class ReportRun(BaseModel):
    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "Excel"
        CSV = "csv", "CSV"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    definition = models.ForeignKey(
        ReportDefinition, on_delete=models.PROTECT, related_name="runs"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_runs",
    )
    format = models.CharField(max_length=5, choices=Format.choices)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.QUEUED
    )
    file = models.FileField(upload_to=report_file_path, null=True, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.definition_id} {self.format} ({self.status})"


# Module-level alias for spectacular ENUM_NAME_OVERRIDES (nested paths fail).
REPORT_RUN_STATUS_CHOICES = ReportRun.Status.choices
