"""Seed the default SMS templates so status triggers work out of the box."""

from django.db import migrations

TEMPLATES = [
    (
        "application_submitted",
        "Dear {name}, your police clearance application {tracking_no} has been "
        "received. Keep this tracking number for status checks.",
        "Sent when an application is submitted.",
    ),
    (
        "payment_received",
        "Dear {name}, payment for application {tracking_no} was received "
        "(receipt {receipt_no}). We will notify you when your certificate is ready.",
        "Sent when the clearance fee is paid.",
    ),
    (
        "certificate_ready",
        "Dear {name}, your police clearance certificate for {tracking_no} is ready "
        "for collection. Verification number: {verification_no}.",
        "Sent when the certificate is issued.",
    ),
]


def seed(apps, schema_editor):
    SmsTemplate = apps.get_model("notifications", "SmsTemplate")
    for code, body, description in TEMPLATES:
        SmsTemplate.objects.get_or_create(
            code=code, defaults={"body": body, "description": description}
        )


def unseed(apps, schema_editor):
    SmsTemplate = apps.get_model("notifications", "SmsTemplate")
    SmsTemplate.objects.filter(code__in=[c for c, _, _ in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
