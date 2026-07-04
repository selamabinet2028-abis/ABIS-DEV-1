"""Base-data services."""

from django.db import connection
from django.utils import timezone


def generate_person_no() -> str:
    """Sequential person number, e.g. P-2026-000042.

    Backed by a dedicated Postgres sequence (migration 0003) — concurrency-safe;
    numbers are globally unique and do not reset per year.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('abis_person_no_seq')")
        (value,) = cursor.fetchone()
    return f"P-{timezone.now().year}-{value:06d}"
