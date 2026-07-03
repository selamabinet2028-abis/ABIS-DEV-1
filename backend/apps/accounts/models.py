import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class Permission(BaseModel):
    """ABIS domain permission catalog.

    Informs role configuration UIs and reporting; endpoint enforcement is done
    by the role-based permission classes in permissions.py (deny-by-default).
    """

    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50)

    class Meta:
        ordering = ["module", "codename"]

    def __str__(self) -> str:
        return self.codename


class Role(BaseModel):
    ADMIN = "admin"
    OPERATOR = "operator"
    INVESTIGATOR = "investigator"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"

    NAME_CHOICES = [
        (ADMIN, "Administrator"),
        (OPERATOR, "Enrollment Operator"),
        (INVESTIGATOR, "Investigator"),
        (SUPERVISOR, "Supervisor"),
        (AUDITOR, "Auditor"),
    ]

    name = models.CharField(max_length=32, unique=True, choices=NAME_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """ABIS user account (see ADR-009 for why this predates T-004)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role, null=True, blank=True, on_delete=models.PROTECT, related_name="users"
    )
    org_unit = models.ForeignKey(
        "basedata.OrgUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    badge_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role_id else None

    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > timezone.now()


class UserActivityLog(models.Model):
    """Authentication/session activity (distinct from audit.AuditLog)."""

    class Action(models.TextChoices):
        LOGIN_SUCCESS = "login_success", "Login success"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGIN_BLOCKED = "login_blocked", "Login blocked (account locked)"
        ACCOUNT_LOCKED = "account_locked", "Account locked"
        LOGOUT = "logout", "Logout"
        PASSWORD_CHANGE = "password_change", "Password change"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )
    username = models.CharField(max_length=150, blank=True)  # as attempted
    action = models.CharField(max_length=32, choices=Action.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.username} {self.action} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
