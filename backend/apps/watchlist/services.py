"""Watchlist alerting: create alerts for DONE match jobs, push over Channels."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import WatchlistAlert, WatchlistEntry

ALERTS_GROUP = "alerts"


def create_alerts_for_job(job) -> list[WatchlistAlert]:
    """One alert per (active entry, job) whose person appears in candidates."""
    best_score_by_person: dict = {}
    for candidate in job.candidates.exclude(person__isnull=True):
        current = best_score_by_person.get(candidate.person_id)
        if current is None or candidate.score > current:
            best_score_by_person[candidate.person_id] = candidate.score
    if not best_score_by_person:
        return []

    entries = WatchlistEntry.objects.filter(
        active=True,
        watchlist__is_active=True,
        person_id__in=best_score_by_person,
    ).select_related("person", "watchlist")

    created_alerts = []
    for entry in entries:
        score = best_score_by_person[entry.person_id]
        alert, created = WatchlistAlert.objects.get_or_create(
            entry=entry,
            trigger_job=job,
            defaults={
                "score": score,
                "message": (
                    f"{entry.person.full_name} ({entry.person.person_no}) matched on "
                    f"'{entry.watchlist.name}' via {job.job_type} at score {score}"
                ),
            },
        )
        if created:
            created_alerts.append(alert)
            push_alert(alert)
    return created_alerts


def push_alert(alert: WatchlistAlert) -> None:
    """Send the alert to the ws/alerts/ group (supervisors + investigators)."""
    from .serializers import WatchlistAlertSerializer

    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        ALERTS_GROUP,
        {"type": "alert.created", "alert": WatchlistAlertSerializer(alert).data},
    )


def acknowledge_alert(alert: WatchlistAlert, user) -> WatchlistAlert:
    if not alert.acknowledged:
        from django.utils import timezone

        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["acknowledged", "acknowledged_by", "acknowledged_at"])
    return alert
