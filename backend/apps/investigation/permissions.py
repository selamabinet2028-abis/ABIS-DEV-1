from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class InvestigationPermission(RoleMatrixPermission):
    """Seed permission cases.manage: investigator (+admin); supervisors read."""

    read_roles = (Role.ADMIN, Role.INVESTIGATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.INVESTIGATOR)
