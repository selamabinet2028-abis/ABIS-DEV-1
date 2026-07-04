import uuid

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from common.models import BaseModel


def person_photo_path(instance: "Person", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"persons/photos/{instance.id}/{uuid.uuid4().hex}.{ext}"


class OrgUnit(BaseModel):
    """Organizational unit hierarchy (created minimal in T-004, CRUD in T-006)."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Person(BaseModel):
    """Person card — the subject of enrollments, cases, and clearances.

    Soft-deleted (evidentiary retention, DATABASE_DESIGN.md): destroy sets
    is_deleted and the API excludes such rows; hard deletes never happen.
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNKNOWN = "unknown", "Unknown"

    person_no = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)  # father name
    last_name = models.CharField(max_length=100, blank=True)  # grandfather name
    gender = models.CharField(
        max_length=10, choices=Gender.choices, default=Gender.UNKNOWN
    )
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=64, default="Ethiopian")
    national_id_no = models.CharField(
        max_length=32, unique=True, null=True, blank=True
    )  # Fayda FIN, when known
    addresses = models.JSONField(default=list, blank=True)
    photo = models.ImageField(upload_to=person_photo_path, null=True, blank=True)
    remarks = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["person_no"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            GinIndex(fields=["addresses"]),
        ]

    def __str__(self) -> str:
        return f"{self.person_no} {self.full_name}"

    @property
    def full_name(self) -> str:
        return " ".join(
            p for p in (self.first_name, self.middle_name, self.last_name) if p
        )

    def save(self, *args, **kwargs):
        if not self.person_no:
            from .services import generate_person_no

            self.person_no = generate_person_no()
        return super().save(*args, **kwargs)


class LookupValue(BaseModel):
    """Standardized code lists (nationalities, purposes, id types, ...)."""

    category = models.CharField(max_length=64, db_index=True)
    code = models.CharField(max_length=64)
    label = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "code"], name="uniq_lookup_category_code"
            )
        ]

    def __str__(self) -> str:
        return f"{self.category}:{self.code}"


class InvestigationCategory(BaseModel):
    """Crime/investigation classification used by cases and enrollment."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "investigation categories"

    def __str__(self) -> str:
        return f"{self.code} {self.name}"
