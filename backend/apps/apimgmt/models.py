from django.conf import settings
from django.db import models

from common.models import BaseModel


class ApiCredential(BaseModel):
    """Hashed machine-to-machine API key.

    Minimal at T-014 (institutional certificate verification needs it);
    ExternalSystem connectors, CRUD and integration logs land with T-017.
    Raw keys look like `<key_prefix>.<secret>` and are shown exactly once.
    """

    name = models.CharField(max_length=150)
    key_prefix = models.CharField(max_length=8, unique=True)
    key_hash = models.CharField(max_length=64)  # sha256(secret)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_api_credentials",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.key_prefix}…)"
