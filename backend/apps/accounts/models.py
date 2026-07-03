import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """ABIS user account.

    Defined at scaffold time so AUTH_USER_MODEL is custom from the first
    migration (swapping it later re-baselines everything). Role FK, org_unit,
    badge_number and lockout fields land with T-004.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"
