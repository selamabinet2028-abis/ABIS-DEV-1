import uuid

from django.conf import settings
from django.db import models


class AuditImmutabilityError(RuntimeError):
    """Raised on any attempt to update or delete audit rows (insert-only)."""


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditImmutabilityError("AuditLog is insert-only: update() is forbidden.")

    def delete(self):
        raise AuditImmutabilityError("AuditLog is insert-only: delete() is forbidden.")

    # bulk_update goes through queryset.update(); bulk_create is allowed.


class AuditLog(models.Model):
    """Insert-only audit trail (DATABASE_DESIGN.md).

    Application-level REVOKE: save() on existing rows, delete(), and
    queryset update()/delete() all raise AuditImmutabilityError. Rows are
    written via apps.audit.services.write_audit / the signal receivers.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        SEARCH = "search", "Search"
        VIEW = "view", "View"
        EXPORT = "export", "Export"
        SYSTEM_ERROR = "system_error", "System error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True)  # snapshot
    action = models.CharField(max_length=16, choices=Action.choices)
    entity = models.CharField(max_length=100)  # app_label.ModelName
    entity_id = models.CharField(max_length=64, blank=True)
    entity_repr = models.CharField(max_length=255, blank=True)  # str() snapshot
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-at"]
        indexes = [models.Index(fields=["entity", "entity_id"])]

    def __str__(self) -> str:
        return f"{self.action} {self.entity}#{self.entity_id} by {self.actor_username or '-'}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutabilityError(
                "AuditLog is insert-only: rows cannot be modified."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutabilityError("AuditLog is insert-only: rows cannot be deleted.")
