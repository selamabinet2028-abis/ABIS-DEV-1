"""Postgres sequence backing generate_person_no() (concurrency-safe)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("basedata", "0002_investigationcategory_lookupvalue_person"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS abis_person_no_seq START 1;",
            reverse_sql="DROP SEQUENCE IF EXISTS abis_person_no_seq;",
        ),
    ]
