from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class WatchlistPermission(RoleMatrixPermission):
    """Seed permission watchlist.manage: investigator + supervisor (+admin)."""

    read_roles = (Role.ADMIN, Role.INVESTIGATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.INVESTIGATOR, Role.SUPERVISOR)
