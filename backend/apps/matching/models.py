from django.conf import settings
from django.db import models

from common.models import BaseModel


class MatchJob(BaseModel):
    """A biometric search job (async via Celery, except VERIFY-1_1).

    Probe is exactly one of: probe_record (TP-*/FACE), probe_enrollment
    (DEDUP — multi-record probe, see ADR-017), probe_latent (LT-*, added
    with T-009).
    """

    class JobType(models.TextChoices):
        TP_TP = "TP-TP", "Tenprint vs tenprint"
        TP_LT = "TP-LT", "Tenprint vs latents"
        LT_TP = "LT-TP", "Latent vs tenprints"
        LT_LT = "LT-LT", "Latent vs latents"
        FACE_1N = "FACE-1N", "Face 1:N"
        VERIFY = "VERIFY-1_1", "Verify 1:1"
        DEDUP = "DEDUP", "Enrollment deduplication"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    job_type = models.CharField(max_length=12, choices=JobType.choices)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.QUEUED
    )
    probe_record = models.ForeignKey(
        "enrollment.BiometricRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="match_jobs",
    )
    probe_enrollment = models.ForeignKey(
        "enrollment.Enrollment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dedup_jobs",
    )
    probe_latent = models.ForeignKey(
        "investigation.LatentPrint",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="match_jobs",
    )
    probe_photo = models.ForeignKey(
        "pis.PhotoProbe",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="match_jobs",
    )
    threshold = models.FloatField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="match_jobs",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.job_type} job {self.id} ({self.status})"


class MatchCandidate(BaseModel):
    """One ranked hit of a match job, pending human decision."""

    class Decision(models.TextChoices):
        UNDECIDED = "undecided", "Undecided"
        HIT = "hit", "Hit"
        NO_HIT = "no_hit", "No hit"

    job = models.ForeignKey(
        MatchJob, on_delete=models.CASCADE, related_name="candidates"
    )
    # Person-database hits carry person+record; latent-file hits carry latent
    # (person unknown by definition). See ADR-018.
    person = models.ForeignKey(
        "basedata.Person",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="match_candidates",
    )
    record = models.ForeignKey(
        "enrollment.BiometricRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="match_candidates",
    )
    latent = models.ForeignKey(
        "investigation.LatentPrint",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="candidate_hits",
    )
    score = models.FloatField()
    rank = models.PositiveSmallIntegerField()
    decision = models.CharField(
        max_length=10, choices=Decision.choices, default=Decision.UNDECIDED
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="candidate_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["job", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "rank"], name="uniq_candidate_job_rank"
            ),
            models.CheckConstraint(
                condition=models.Q(record__isnull=False)
                | models.Q(latent__isnull=False),
                name="candidate_has_record_or_latent",
            ),
        ]

    def __str__(self) -> str:
        target = self.person_id or self.latent_id
        return f"#{self.rank} {target} @ {self.score} ({self.decision})"


# Module-level aliases for spectacular ENUM_NAME_OVERRIDES (nested paths fail).
MATCH_JOB_TYPE_CHOICES = MatchJob.JobType.choices
MATCH_JOB_STATUS_CHOICES = MatchJob.Status.choices
