from apps.accounts.models import Role
from apps.accounts.permissions import RoleMatrixPermission


class PersonPermission(RoleMatrixPermission):
    """Seed permission matrix: persons.view / persons.manage."""

    read_roles = (Role.ADMIN, Role.OPERATOR, Role.INVESTIGATOR, Role.SUPERVISOR)
    write_roles = (Role.ADMIN, Role.OPERATOR)


class BaseDataAdminWrite(RoleMatrixPermission):
    """Org units, lookups, categories: any staff role reads, admin writes."""

    read_roles = (
        Role.ADMIN,
        Role.OPERATOR,
        Role.INVESTIGATOR,
        Role.SUPERVISOR,
        Role.AUDITOR,
    )
    write_roles = (Role.ADMIN,)
