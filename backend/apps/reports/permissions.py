from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class ReportPermission(RoleMatrixPermission):
    """Seed permission reports.view: supervisor + auditor (+admin).
    Running a report is a read-only data export, so all three may POST."""

    read_roles = (Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR)
    write_roles = (Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR)


class KpiPermission(RoleMatrixPermission):
    """Every staff role sees its scoped dashboard blocks."""

    read_roles = (
        Role.ADMIN,
        Role.OPERATOR,
        Role.INVESTIGATOR,
        Role.SUPERVISOR,
        Role.AUDITOR,
    )
    write_roles = ()
