from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class DecisionPermission(RoleMatrixPermission):
    """Approval decisions are review work: supervisor (+admin)."""

    read_roles = (Role.ADMIN, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.SUPERVISOR)


class CertificatePermission(RoleMatrixPermission):
    """Seed permission certificates.issue: operator (+supervisor/admin)."""

    read_roles = (Role.ADMIN, Role.OPERATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.OPERATOR, Role.SUPERVISOR)
