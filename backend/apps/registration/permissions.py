from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class ApplicationPermission(RoleMatrixPermission):
    """Seed permission applications.process: operator + supervisor (+admin)."""

    read_roles = (Role.ADMIN, Role.OPERATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.OPERATOR, Role.SUPERVISOR)
