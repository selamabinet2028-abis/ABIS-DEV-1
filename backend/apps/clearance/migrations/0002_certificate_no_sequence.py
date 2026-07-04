"""Postgres sequence backing generate_certificate_no() (concurrency-safe)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("clearance", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS abis_certificate_no_seq START 1;",
            reverse_sql="DROP SEQUENCE IF EXISTS abis_certificate_no_seq;",
        ),
    ]
