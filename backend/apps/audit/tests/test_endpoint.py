"""T-005: /audit-logs/ read-only endpoint — RBAC + filters."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import write_audit

pytestmark = pytest.mark.django_db

URL = "/api/v1/audit-logs/"


@pytest.fixture
def sample_rows(db):
    write_audit(AuditLog.Action.CREATE, entity="basedata.Person", entity_id="p-1")
    write_audit(AuditLog.Action.UPDATE, entity="basedata.Person", entity_id="p-1")
    write_audit(AuditLog.Action.DELETE, entity="accounts.Role", entity_id="r-1")


class TestAccess:
    @pytest.mark.parametrize(
        "role,expected",
        [
            ("admin", 200),
            ("auditor", 200),
            ("operator", 403),
            ("investigator", 403),
            ("supervisor", 403),
        ],
    )
    def test_list_rbac(self, auth_client, role, expected):
        assert auth_client(role).get(URL).status_code == expected

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(URL).status_code == 401

    def test_auditor_cannot_post(self, auth_client):
        # read_only gate rejects before method routing
        assert auth_client("auditor").post(URL, {}, format="json").status_code == 403

    def test_admin_post_method_not_allowed(self, auth_client):
        # admin passes RBAC, but the viewset is read-only
        assert auth_client("admin").post(URL, {}, format="json").status_code == 405


class TestFilters:
    def test_filter_by_entity_and_entity_id(self, auth_client, sample_rows):
        client = auth_client("auditor")
        resp = client.get(URL, {"entity": "basedata.Person", "entity_id": "p-1"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 2
        assert all(r["entity"] == "basedata.Person" for r in results)

    def test_filter_by_action(self, auth_client, sample_rows):
        resp = auth_client("auditor").get(URL, {"action": "delete"})
        rows = resp.json()["results"]
        assert [r["entity"] for r in rows] == ["accounts.Role"]

    def test_filter_by_actor(self, auth_client, sample_rows):
        client = auth_client("admin")
        # mutate something over the API so an actor is attributed
        client.patch(
            f"/api/v1/users/{client.user.id}/", {"phone": "0911"}, format="json"
        )
        resp = client.get(URL, {"actor": client.user.username})
        assert resp.status_code == 200
        rows = resp.json()["results"]
        assert rows and all(r["actor_username"] == client.user.username for r in rows)

    def test_date_range_filter(self, auth_client, sample_rows):
        future = (timezone.now() + timedelta(hours=1)).isoformat()
        resp = auth_client("auditor").get(URL, {"date_from": future})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
