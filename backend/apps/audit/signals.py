"""Generic mutation tracking for models listed in settings.ABIS_AUDITED_MODELS.

pre_save stashes the persisted field values; post_save writes a create row or
an old→new diff; post_delete writes a snapshot. Sensitive fields are masked,
noise-only updates (e.g. last_login) are skipped.
"""
from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Any

from django.apps import apps as django_apps
from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save

from .models import AuditLog
from .services import audit_instance

_OLD_VALUES_ATTR = "_audit_old_values"

MASK = "***"


def _mask_fields() -> set[str]:
    return set(getattr(settings, "ABIS_AUDIT_MASK_FIELDS", {"password"}))


def _ignore_fields() -> set[str]:
    return set(getattr(settings, "ABIS_AUDIT_IGNORE_FIELDS", {"last_login", "updated_at"}))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (uuid.UUID, decimal.Decimal)):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _field_values(instance) -> dict[str, Any]:
    values = {}
    for field in instance._meta.concrete_fields:
        name = field.attname  # FKs recorded as <name>_id
        raw = getattr(instance, name)
        base = name.removesuffix("_id")
        if base in _mask_fields() or name in _mask_fields():
            raw = MASK if raw else raw
        values[name] = _json_safe(raw)
    return values


def _on_pre_save(sender, instance, raw=False, **kwargs):
    if raw or instance.pk is None:
        return
    old = sender._default_manager.filter(pk=instance.pk).first()
    if old is not None:
        setattr(instance, _OLD_VALUES_ATTR, _field_values(old))


def _on_post_save(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        audit_instance(AuditLog.Action.CREATE, instance, changes={"new": _field_values(instance)})
        return

    old_values = getattr(instance, _OLD_VALUES_ATTR, None)
    if old_values is None:
        return  # unsaved-before instance or untracked path
    new_values = _field_values(instance)
    ignored = _ignore_fields()
    diff = {
        name: {"old": old_values.get(name), "new": new}
        for name, new in new_values.items()
        if name not in ignored and old_values.get(name) != new
    }
    if diff:
        audit_instance(AuditLog.Action.UPDATE, instance, changes=diff)


def _on_post_delete(sender, instance, **kwargs):
    audit_instance(AuditLog.Action.DELETE, instance, changes={"old": _field_values(instance)})


def connect_audited_models() -> list[str]:
    """Wire signal receivers for every label in ABIS_AUDITED_MODELS."""
    connected = []
    for label in getattr(settings, "ABIS_AUDITED_MODELS", []):
        model = django_apps.get_model(label)
        uid = f"audit:{label}"
        pre_save.connect(_on_pre_save, sender=model, dispatch_uid=f"{uid}:pre_save")
        post_save.connect(_on_post_save, sender=model, dispatch_uid=f"{uid}:post_save")
        post_delete.connect(_on_post_delete, sender=model, dispatch_uid=f"{uid}:post_delete")
        connected.append(label)
    return connected
