"""T-004: login/lockout/refresh rotation/logout/password change."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserActivityLog

from .factories import DEFAULT_PASSWORD

LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"
PASSWORD_URL = "/api/v1/auth/password/change/"
COOKIE = settings.ABIS_AUTH["REFRESH_COOKIE_NAME"]

pytestmark = pytest.mark.django_db


def login(client, username, password=DEFAULT_PASSWORD):
    return client.post(
        LOGIN_URL, {"username": username, "password": password}, format="json"
    )


class TestLogin:
    def test_success_returns_access_user_and_refresh_cookie(
        self, api_client, make_user
    ):
        user = make_user("operator")
        resp = login(api_client, user.username)
        assert resp.status_code == 200
        body = resp.json()
        assert body["access"]
        assert "refresh" not in body  # refresh travels only in the httpOnly cookie
        assert body["user"]["username"] == user.username
        assert body["user"]["role"] == "operator"
        morsel = resp.cookies[COOKIE]
        assert morsel.value
        assert morsel["httponly"]
        assert morsel["path"] == settings.ABIS_AUTH["REFRESH_COOKIE_PATH"]
        assert UserActivityLog.objects.filter(
            user=user, action=UserActivityLog.Action.LOGIN_SUCCESS
        ).exists()

    def test_wrong_password_401_and_counter_increments(self, api_client, make_user):
        user = make_user("operator")
        resp = login(api_client, user.username, "wrong-password")
        assert resp.status_code == 401
        user.refresh_from_db()
        assert user.failed_login_attempts == 1
        assert UserActivityLog.objects.filter(
            user=user, action=UserActivityLog.Action.LOGIN_FAILED
        ).exists()

    def test_unknown_username_401_logged_without_user(self, api_client, db):
        resp = login(api_client, "ghost", "whatever")
        assert resp.status_code == 401
        assert UserActivityLog.objects.filter(
            username="ghost", action=UserActivityLog.Action.LOGIN_FAILED, user=None
        ).exists()

    def test_inactive_user_cannot_login(self, api_client, make_user):
        user = make_user("operator", is_active=False)
        resp = login(api_client, user.username)
        assert resp.status_code == 401


class TestLockout:
    def test_lockout_after_threshold_failures(self, api_client, make_user):
        user = make_user("operator")
        threshold = settings.ABIS_AUTH["LOCKOUT_THRESHOLD"]
        for _ in range(threshold):
            login(api_client, user.username, "wrong-password")
        user.refresh_from_db()
        assert user.locked_until is not None and user.locked_until > timezone.now()
        assert UserActivityLog.objects.filter(
            user=user, action=UserActivityLog.Action.ACCOUNT_LOCKED
        ).exists()

        # Correct password is still rejected while locked.
        resp = login(api_client, user.username)
        assert resp.status_code == 403
        assert UserActivityLog.objects.filter(
            user=user, action=UserActivityLog.Action.LOGIN_BLOCKED
        ).exists()

    def test_lock_expires_and_login_succeeds(self, api_client, make_user):
        user = make_user("operator")
        user.locked_until = timezone.now() - timedelta(seconds=1)
        user.failed_login_attempts = 0
        user.save(update_fields=["locked_until", "failed_login_attempts"])

        resp = login(api_client, user.username)
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.locked_until is None
        assert user.failed_login_attempts == 0


class TestRefresh:
    def test_refresh_rotates_cookie_and_blacklists_old(self, api_client, make_user):
        user = make_user("operator")
        login(api_client, user.username)
        old_refresh = api_client.cookies[COOKIE].value

        resp = api_client.post(REFRESH_URL, {}, format="json")
        assert resp.status_code == 200
        assert resp.json()["access"]
        new_refresh = resp.cookies[COOKIE].value
        assert new_refresh and new_refresh != old_refresh

        # Old (rotated-away) token must be rejected.
        stale = APIClient()
        stale.cookies[COOKIE] = old_refresh
        resp2 = stale.post(REFRESH_URL, {}, format="json")
        assert resp2.status_code == 401

    def test_refresh_without_cookie_401(self, api_client, db):
        resp = api_client.post(REFRESH_URL, {}, format="json")
        assert resp.status_code == 401

    def test_refresh_body_fallback_for_api_clients(self, api_client, make_user):
        user = make_user("operator")
        login_resp = login(api_client, user.username)
        raw = login_resp.cookies[COOKIE].value

        bare = APIClient()  # no cookie jar — token in body instead
        resp = bare.post(REFRESH_URL, {"refresh": raw}, format="json")
        assert resp.status_code == 200
        assert resp.json()["access"]


class TestLogout:
    def test_logout_blacklists_and_clears_cookie(self, api_client, make_user):
        user = make_user("operator")
        login(api_client, user.username)
        refresh_before = api_client.cookies[COOKIE].value

        resp = api_client.post(LOGOUT_URL, {}, format="json")
        assert resp.status_code == 205
        assert resp.cookies[COOKIE].value == ""  # deletion morsel

        stale = APIClient()
        stale.cookies[COOKIE] = refresh_before
        assert stale.post(REFRESH_URL, {}, format="json").status_code == 401
        assert UserActivityLog.objects.filter(
            user=user, action=UserActivityLog.Action.LOGOUT
        ).exists()


class TestPasswordChange:
    def test_requires_authentication(self, api_client, db):
        resp = api_client.post(
            PASSWORD_URL,
            {"current_password": "x", "new_password": "y"},
            format="json",
        )
        assert resp.status_code == 401

    def test_wrong_current_password_400(self, api_client, make_user):
        user = make_user("operator")
        login_resp = login(api_client, user.username)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.json()['access']}"
        )
        resp = api_client.post(
            PASSWORD_URL,
            {"current_password": "nope", "new_password": "N3w!Passw0rd42"},
            format="json",
        )
        assert resp.status_code == 400
        assert "current_password" in resp.json()

    def test_weak_new_password_rejected(self, api_client, make_user):
        user = make_user("operator")
        login_resp = login(api_client, user.username)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.json()['access']}"
        )
        resp = api_client.post(
            PASSWORD_URL,
            {"current_password": DEFAULT_PASSWORD, "new_password": "short"},
            format="json",
        )
        assert resp.status_code == 400
        assert "new_password" in resp.json()

    def test_success_rotates_credentials(self, api_client, make_user):
        user = make_user("operator", must_change_password=True)
        login_resp = login(api_client, user.username)
        old_refresh = login_resp.cookies[COOKIE].value
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.json()['access']}"
        )

        new_password = "N3w!Passw0rd42"
        resp = api_client.post(
            PASSWORD_URL,
            {"current_password": DEFAULT_PASSWORD, "new_password": new_password},
            format="json",
        )
        assert resp.status_code == 200

        user.refresh_from_db()
        assert user.check_password(new_password)
        assert user.must_change_password is False
        assert user.password_changed_at is not None

        # Old refresh tokens are blacklisted.
        stale = APIClient()
        stale.cookies[COOKIE] = old_refresh
        assert stale.post(REFRESH_URL, {}, format="json").status_code == 401

        # And the new password logs in.
        fresh = APIClient()
        assert login(fresh, user.username, new_password).status_code == 200
