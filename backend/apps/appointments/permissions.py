from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class AppointmentStaffPermission(RoleMatrixPermission):
    """Front-desk scheduling: operators manage, supervisors read (+admin)."""

    read_roles = (Role.ADMIN, Role.OPERATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.OPERATOR)


class StationAdminPermission(RoleMatrixPermission):
    """Stations/slots: any staff role reads, admin writes."""

    read_roles = (
        Role.ADMIN,
        Role.OPERATOR,
        Role.INVESTIGATOR,
        Role.SUPERVISOR,
        Role.AUDITOR,
    )
    write_roles = (Role.ADMIN,)
