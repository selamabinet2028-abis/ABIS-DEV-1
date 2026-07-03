"""T-004: users/roles CRUD behavior (admin paths)."""

import pytest

from apps.accounts.models import Role, User, UserActivityLog
from apps.accounts.services import log_activity

from .factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db

USERS_URL = "/api/v1/users/"


@pytest.fixture
def admin_client(auth_client):
    return auth_client("admin")


class TestUserCrud:
    def test_create_user_with_role(self, admin_client):
        role_id = str(Role.objects.get(name="investigator").id)
        resp = admin_client.post(
            USERS_URL,
            {
                "username": "det.alemu",
                "email": "alemu@efpc.gov.et",
                "password": "Val1d!Passw0rd42",
                "first_name": "Alemu",
                "last_name": "Tesfaye",
                "badge_number": "EFP-90001",
                "role": role_id,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["role"] == "investigator"
        assert "password" not in body
        user = User.objects.get(username="det.alemu")
        assert user.check_password("Val1d!Passw0rd42")

    def test_create_rejects_weak_password(self, admin_client):
        resp = admin_client.post(
            USERS_URL,
            {"username": "weak", "email": "w@efpc.gov.et", "password": "12345678"},
            format="json",
        )
        assert resp.status_code == 400
        assert "password" in resp.json()

    def test_search_by_badge_number(self, admin_client, make_user):
        make_user("operator", username="findme", badge_number="EFP-77777")
        resp = admin_client.get(USERS_URL, {"search": "EFP-77777"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["username"] == "findme"

    def test_patch_role(self, admin_client, make_user):
        user = make_user("operator")
        supervisor_id = str(Role.objects.get(name="supervisor").id)
        resp = admin_client.patch(
            f"{USERS_URL}{user.id}/", {"role": supervisor_id}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "supervisor"

    def test_patch_cannot_set_password(self, admin_client, make_user):
        user = make_user("operator")
        resp = admin_client.patch(
            f"{USERS_URL}{user.id}/", {"password": "Sneaky!Passw0rd42"}, format="json"
        )
        assert resp.status_code == 200  # unknown field ignored
        user.refresh_from_db()
        assert user.check_password(DEFAULT_PASSWORD)  # unchanged

    def test_delete_deactivates_instead_of_deleting(
        self, admin_client, make_user, api_client
    ):
        user = make_user("operator")
        resp = admin_client.delete(f"{USERS_URL}{user.id}/")
        assert resp.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False
        assert User.objects.filter(id=user.id).exists()  # still in the DB

        # Deactivated user cannot log in.
        login = api_client.post(
            "/api/v1/auth/login/",
            {"username": user.username, "password": DEFAULT_PASSWORD},
            format="json",
        )
        assert login.status_code == 401

    def test_activity_lists_user_rows(self, admin_client, make_user):
        user = make_user("operator")
        log_activity(UserActivityLog.Action.LOGIN_SUCCESS, user=user)
        log_activity(UserActivityLog.Action.LOGOUT, user=user)
        resp = admin_client.get(f"{USERS_URL}{user.id}/activity/")
        assert resp.status_code == 200
        actions = [r["action"] for r in resp.json()["results"]]
        assert "login_success" in actions and "logout" in actions


class TestRoleApi:
    def test_seeded_roles_present_with_permissions(self, admin_client):
        resp = admin_client.get("/api/v1/roles/")
        assert resp.status_code == 200
        by_name = {r["name"]: r for r in resp.json()["results"]}
        assert set(by_name) == {
            "admin",
            "operator",
            "investigator",
            "supervisor",
            "auditor",
        }
        assert "audit.view" in by_name["auditor"]["permissions"]
        assert len(by_name["admin"]["permissions"]) == 15

    def test_update_role_description(self, admin_client):
        role = Role.objects.get(name="operator")
        resp = admin_client.patch(
            f"/api/v1/roles/{role.id}/", {"description": "Front desk"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Front desk"

    def test_role_with_users_cannot_be_deleted(self, admin_client, make_user):
        make_user("auditor")
        role = Role.objects.get(name="auditor")
        resp = admin_client.delete(f"/api/v1/roles/{role.id}/")
        assert resp.status_code == 409
        assert Role.objects.filter(id=role.id).exists()
