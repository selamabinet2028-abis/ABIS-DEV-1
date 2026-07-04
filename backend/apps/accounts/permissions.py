"""RBAC permission classes — deny by default (golden rule).

Admin (or superuser) passes every role gate. Compose with `|` where an
endpoint serves several roles, e.g. `IsAdmin | IsAuditorReadOnly`.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


class RolePermission(BasePermission):
    allowed_roles: tuple[str, ...] = ()
    read_only = False

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        role = getattr(user, "role_name", None)
        if role is None:
            return False
        if self.read_only and request.method not in SAFE_METHODS:
            return False
        return role in self.allowed_roles


class IsAdmin(RolePermission):
    allowed_roles = (Role.ADMIN,)


class IsOperator(RolePermission):
    allowed_roles = (Role.ADMIN, Role.OPERATOR)


class IsInvestigator(RolePermission):
    allowed_roles = (Role.ADMIN, Role.INVESTIGATOR)


class IsSupervisor(RolePermission):
    allowed_roles = (Role.ADMIN, Role.SUPERVISOR)


class IsAuditorReadOnly(RolePermission):
    allowed_roles = (Role.ADMIN, Role.AUDITOR)
    read_only = True


class RoleMatrixPermission(BasePermission):
    """Different role sets for read (SAFE_METHODS) vs write. Subclass per
    resource — see e.g. apps.basedata.permissions."""

    read_roles: tuple[str, ...] = ()
    write_roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        role = getattr(user, "role_name", None)
        if role is None:
            return False
        allowed = (
            self.read_roles if request.method in SAFE_METHODS else self.write_roles
        )
        return role in allowed
