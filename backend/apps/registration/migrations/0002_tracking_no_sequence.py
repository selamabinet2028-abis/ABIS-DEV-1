"""Postgres sequence backing generate_tracking_no() (concurrency-safe)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("registration", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS abis_tracking_no_seq START 1;",
            reverse_sql="DROP SEQUENCE IF EXISTS abis_tracking_no_seq;",
        ),
    ]
