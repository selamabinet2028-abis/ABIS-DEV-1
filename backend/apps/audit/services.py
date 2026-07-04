"""Audit write helpers. All AuditLog rows are created through here."""

from __future__ import annotations

from typing import Any

from django.db import models

from .middleware import get_current_request
from .models import AuditLog


def _request_meta() -> dict[str, Any]:
    request = get_current_request()
    if request is None:
        return {"actor": None, "actor_username": "", "ip": None, "user_agent": ""}
    user = getattr(request, "user", None)
    actor = user if (user is not None and user.is_authenticated) else None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else request.META.get("REMOTE_ADDR")
    )
    return {
        "actor": actor,
        "actor_username": actor.username if actor else "",
        "ip": ip,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
    }


def write_audit(
    action: str,
    *,
    entity: str,
    entity_id: str = "",
    entity_repr: str = "",
    changes: dict | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        entity_repr=entity_repr[:255],
        changes=changes or {},
        **_request_meta(),
    )


def audit_instance(
    action: str, instance: models.Model, changes: dict | None = None
) -> AuditLog:
    return write_audit(
        action,
        entity=instance._meta.label,
        entity_id=str(instance.pk),
        entity_repr=str(instance),
        changes=changes,
    )


def log_search(entity: str, params: dict) -> AuditLog:
    """Search auditing for person/biometric endpoints (wired in from T-006)."""
    clean = {k: v for k, v in params.items() if v not in ("", None)}
    return write_audit(AuditLog.Action.SEARCH, entity=entity, changes={"query": clean})
