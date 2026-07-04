from django.conf import settings
from django.db import models

from common.models import BaseModel


class Watchlist(BaseModel):
    class ListType(models.TextChoices):
        CRIMINAL = "criminal", "Criminal"
        TERRORIST = "terrorist", "Terrorist"
        IMMIGRATION_BLACKLIST = "immigration_blacklist", "Immigration blacklist"
        FRAUD = "fraud", "Fraud"

    name = models.CharField(max_length=255, unique=True)
    list_type = models.CharField(max_length=32, choices=ListType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_watchlists",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.list_type})"


class WatchlistEntry(BaseModel):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    watchlist = models.ForeignKey(
        Watchlist, on_delete=models.CASCADE, related_name="entries"
    )
    person = models.ForeignKey(
        "basedata.Person", on_delete=models.PROTECT, related_name="watchlist_entries"
    )
    reason = models.CharField(max_length=500)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    active = models.BooleanField(default=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="added_watchlist_entries",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["watchlist", "person"], name="uniq_entry_watchlist_person"
            )
        ]

    def __str__(self) -> str:
        return f"{self.person_id} on {self.watchlist_id} ({self.severity})"


class WatchlistAlert(BaseModel):
    """Fired when a DONE match job produces a candidate on an active list."""

    entry = models.ForeignKey(
        WatchlistEntry, on_delete=models.PROTECT, related_name="alerts"
    )
    trigger_job = models.ForeignKey(
        "matching.MatchJob", on_delete=models.PROTECT, related_name="watchlist_alerts"
    )
    score = models.FloatField()
    message = models.CharField(max_length=500, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acknowledged_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "trigger_job"], name="uniq_alert_entry_job"
            )
        ]
        indexes = [models.Index(fields=["acknowledged", "created_at"])]

    def __str__(self) -> str:
        return f"Alert {self.id} ({'ack' if self.acknowledged else 'open'})"
