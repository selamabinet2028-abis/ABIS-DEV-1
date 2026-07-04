"""Seed the five standard report definitions (TASK_QUEUE T-016)."""

from django.db import migrations

DEFINITIONS = [
    (
        "enrollment_stats",
        "Enrollment Statistics",
        "Enrollments and biometric records by status/modality.",
    ),
    (
        "verification_outcomes",
        "Verification Outcomes",
        "Certificate verifications by channel and result.",
    ),
    (
        "case_activity",
        "Case Activity",
        "Cases by status, latents, confirmed hits, evidence.",
    ),
    (
        "duplicates",
        "Potential Duplicates",
        "DEDUP job candidates — possible duplicate identities.",
    ),
    (
        "clearance_issuance",
        "Clearance Issuance",
        "Applications by status, certificates issued, fees collected.",
    ),
]


def seed(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    for code, name, description in DEFINITIONS:
        ReportDefinition.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": description, "query_key": code},
        )


def unseed(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(code__in=[c for c, _, _ in DEFINITIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
