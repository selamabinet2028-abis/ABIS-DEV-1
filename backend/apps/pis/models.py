import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModel


def probe_photo_path(instance: "PhotoProbe", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"pis/probes/{uuid.uuid4().hex}.{ext}"


class PhotoProbe(BaseModel):
    """An uploaded face photo used as a FACE-1N probe (ADR-019).

    Kept for the review UI and the audit trail — the search job references it
    via MatchJob.probe_photo.
    """

    image = models.FileField(upload_to=probe_photo_path)
    sha256 = models.CharField(max_length=64)
    notes = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photo_probes",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PhotoProbe {self.id}"
