from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class NotificationPermission(RoleMatrixPermission):
    """Outbox visible to admin/supervisor; templates + test sends admin-only."""

    read_roles = (Role.ADMIN, Role.SUPERVISOR)
    write_roles = (Role.ADMIN,)
