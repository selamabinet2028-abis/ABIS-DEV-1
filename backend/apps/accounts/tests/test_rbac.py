"""T-004: RBAC deny-by-default matrix over real endpoints."""

import pytest

from apps.accounts.models import Role

pytestmark = pytest.mark.django_db

ALL_ROLES = [
    Role.ADMIN,
    Role.OPERATOR,
    Role.INVESTIGATOR,
    Role.SUPERVISOR,
    Role.AUDITOR,
]


NEW_USER_PAYLOAD = {
    "username": "matrix-probe",
    "email": "probe@efpc.gov.et",
    "password": "Pr0be!Passw0rd42",
    "first_name": "Probe",
    "last_name": "User",
}


class TestDenyByDefaultMatrix:
    @pytest.mark.parametrize(
        "role,expected",
        [("admin", 200)] + [(r, 403) for r in ALL_ROLES if r != "admin"],
    )
    def test_list_users(self, auth_client, role, expected):
        assert auth_client(role).get("/api/v1/users/").status_code == expected

    def test_list_users_anonymous_401(self, api_client, db):
        assert api_client.get("/api/v1/users/").status_code == 401

    @pytest.mark.parametrize(
        "role,expected",
        [("admin", 201)] + [(r, 403) for r in ALL_ROLES if r != "admin"],
    )
    def test_create_user(self, auth_client, role, expected):
        resp = auth_client(role).post("/api/v1/users/", NEW_USER_PAYLOAD, format="json")
        assert resp.status_code == expected

    def test_create_user_anonymous_401(self, api_client, db):
        resp = api_client.post("/api/v1/users/", NEW_USER_PAYLOAD, format="json")
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "role,expected",
        [("admin", 200)] + [(r, 403) for r in ALL_ROLES if r != "admin"],
    )
    def test_list_roles(self, auth_client, role, expected):
        assert auth_client(role).get("/api/v1/roles/").status_code == expected

    @pytest.mark.parametrize(
        "role,expected",
        [("admin", 200)] + [(r, 403) for r in ALL_ROLES if r != "admin"],
    )
    def test_list_permissions(self, auth_client, role, expected):
        assert auth_client(role).get("/api/v1/permissions/").status_code == expected

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_me_allowed_for_every_authenticated_role(self, auth_client, role):
        resp = auth_client(role).get("/api/v1/users/me/")
        assert resp.status_code == 200
        assert resp.json()["role"] == role

    def test_me_anonymous_401(self, api_client, db):
        assert api_client.get("/api/v1/users/me/").status_code == 401

    def test_user_without_role_denied_on_role_gated_endpoints(self, auth_client):
        client = auth_client(None)  # authenticated but role-less → deny by default
        assert client.get("/api/v1/users/").status_code == 403
        assert client.get("/api/v1/users/me/").status_code == 200

    @pytest.mark.parametrize(
        "role,expected",
        [
            ("admin", 200),
            ("auditor", 200),  # read-only role may read activity
            ("operator", 403),
            ("investigator", 403),
            ("supervisor", 403),
        ],
    )
    def test_activity_endpoint_admin_and_auditor_only(
        self, auth_client, make_user, role, expected
    ):
        target = make_user("operator")
        resp = auth_client(role).get(f"/api/v1/users/{target.id}/activity/")
        assert resp.status_code == expected

    def test_superuser_passes_role_gates(self, api_client, make_user):
        su = make_user(None, is_superuser=True, is_staff=True)
        api_client.force_authenticate(user=su)
        assert api_client.get("/api/v1/users/").status_code == 200
