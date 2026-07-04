import uuid

from django.conf import settings
from django.db import models

from common.models import BaseModel


def latent_image_path(instance: "LatentPrint", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"latents/{instance.case_id}/{uuid.uuid4().hex}.{ext}"


def latent_enhanced_path(instance: "LatentPrint", filename: str) -> str:
    return f"latents/{instance.case_id}/enhanced-{uuid.uuid4().hex}.png"


def evidence_file_path(instance: "EvidenceDocument", filename: str) -> str:
    safe_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"evidence/{instance.case_id}/{uuid.uuid4().hex}.{safe_ext}"


class Case(BaseModel):
    """Forensic investigation case."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    case_no = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        "basedata.InvestigationCategory",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cases",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    lead_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="led_cases",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.case_no} {self.title}"

    def save(self, *args, **kwargs):
        if not self.case_no:
            from .services import generate_case_no

            self.case_no = generate_case_no()
        return super().save(*args, **kwargs)


class LatentPrint(BaseModel):
    """Latent finger/palm print lifted at a crime scene.

    `editor_history` records every enhance/minutiae action (who, when, ops,
    result sha256) — the working image for searches is `enhanced_image`
    when present, else the original.
    """

    class Modality(models.TextChoices):
        FINGER = "finger", "Fingerprint"
        PALM = "palm", "Palmprint"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="latents")
    modality = models.CharField(max_length=8, choices=Modality.choices)
    image = models.FileField(upload_to=latent_image_path)
    enhanced_image = models.FileField(
        upload_to=latent_enhanced_path, null=True, blank=True
    )
    sha256 = models.CharField(max_length=64)
    minutiae = models.JSONField(default=list, blank=True)
    editor_history = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_latents",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["case", "modality"])]

    def __str__(self) -> str:
        return f"Latent {self.id} ({self.modality}) in {self.case_id}"

    def working_image_field(self):
        return self.enhanced_image if self.enhanced_image else self.image


class EvidenceDocument(BaseModel):
    """Case evidence file with chain-of-custody fields."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="evidence")
    file = models.FileField(upload_to=evidence_file_path)
    description = models.CharField(max_length=255, blank=True)
    collected_by = models.CharField(max_length=150)  # officer name/badge
    collected_at = models.DateTimeField()
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_evidence",
    )

    class Meta:
        ordering = ["-collected_at"]

    def __str__(self) -> str:
        return f"Evidence {self.id} for {self.case_id}"


# Module-level alias for spectacular ENUM_NAME_OVERRIDES (nested paths fail).
LATENT_MODALITY_CHOICES = LatentPrint.Modality.choices
