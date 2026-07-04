from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class EnrollmentPermission(RoleMatrixPermission):
    """Capture is operator work (enrollment.capture); investigators and
    supervisors read for matching/oversight; auditor has no biometric access."""

    read_roles = (Role.ADMIN, Role.OPERATOR, Role.INVESTIGATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.OPERATOR)
