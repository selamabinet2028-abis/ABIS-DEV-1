from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class MatchingRunPermission(RoleMatrixPermission):
    """Seed permission matching.run: investigator + supervisor (+admin)."""

    read_roles = (Role.ADMIN, Role.INVESTIGATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.INVESTIGATOR, Role.SUPERVISOR)


class CandidateDecisionPermission(RoleMatrixPermission):
    """Seed permission matching.decide: investigator only (+admin)."""

    read_roles = (Role.ADMIN, Role.INVESTIGATOR)
    write_roles = (Role.ADMIN, Role.INVESTIGATOR)
