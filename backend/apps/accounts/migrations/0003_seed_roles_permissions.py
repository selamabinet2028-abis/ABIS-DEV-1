"""Seed the five ABIS roles and the domain permission catalog.

Runs in every environment (including test DBs), so RBAC fixtures are always
present after `migrate`.
"""

from django.db import migrations

PERMISSIONS = [
    ("persons.view", "View person records", "basedata"),
    ("persons.manage", "Create and update person records", "basedata"),
    ("enrollment.capture", "Capture biometric enrollments", "enrollment"),
    ("matching.run", "Run identification/verification searches", "matching"),
    ("matching.decide", "Decide match candidates", "matching"),
    ("cases.manage", "Manage investigation cases and latents", "investigation"),
    ("watchlist.manage", "Manage watchlists and alerts", "watchlist"),
    ("applications.process", "Process clearance applications", "registration"),
    ("payments.view", "View payments and reconciliation", "payments"),
    ("certificates.issue", "Issue clearance certificates", "clearance"),
    ("reports.view", "Run and view reports", "reports"),
    ("audit.view", "View audit logs", "audit"),
    ("users.manage", "Manage users and roles", "accounts"),
    ("devices.manage", "Manage capture devices", "devices"),
    ("integrations.manage", "Manage external system connectors", "apimgmt"),
]

ROLES = {
    "admin": (
        "Full system administration",
        [c for c, _, _ in PERMISSIONS],
    ),
    "operator": (
        "Enrollment and clearance front-desk operations",
        [
            "persons.view",
            "persons.manage",
            "enrollment.capture",
            "applications.process",
            "payments.view",
            "certificates.issue",
        ],
    ),
    "investigator": (
        "Forensic and biometric investigation",
        [
            "persons.view",
            "matching.run",
            "matching.decide",
            "cases.manage",
            "watchlist.manage",
        ],
    ),
    "supervisor": (
        "Operational oversight and reporting",
        [
            "persons.view",
            "matching.run",
            "watchlist.manage",
            "applications.process",
            "payments.view",
            "reports.view",
        ],
    ),
    "auditor": (
        "Read-only audit and compliance review",
        ["audit.view", "reports.view"],
    ),
}


def seed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")

    perms = {}
    for codename, name, module in PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename, defaults={"name": name, "module": module}
        )
        perms[codename] = perm

    for role_name, (description, codenames) in ROLES.items():
        role, _ = Role.objects.get_or_create(
            name=role_name, defaults={"description": description}
        )
        role.permissions.set([perms[c] for c in codenames])


def unseed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    Role.objects.filter(name__in=ROLES).delete()
    Permission.objects.filter(codename__in=[c for c, _, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_permission_user_badge_number_and_more"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
