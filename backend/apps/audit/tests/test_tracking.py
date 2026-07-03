"""T-005: mutations on tracked models write audit rows (signals + middleware)."""
import pytest

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.basedata.models import OrgUnit

pytestmark = pytest.mark.django_db


class TestMutationTracking:
    def test_create_writes_audit_row_with_masked_password(self):
        from apps.accounts.models import User

        user = User.objects.create_user(username="tracked.user", password="Tr@cked!Pass42")
        row = AuditLog.objects.get(
            entity="accounts.User", entity_id=str(user.id), action=AuditLog.Action.CREATE
        )
        assert row.changes["new"]["username"] == "tracked.user"
        assert row.changes["new"]["password"] == "***"  # hash never leaks into audit

    def test_password_change_update_row_is_masked(self):
        user = UserFactory(username="rehash.user")
        user.set_password("N3w!Secret42x")
        user.save(update_fields=["password"])
        row = (
            AuditLog.objects.filter(
                entity="accounts.User", entity_id=str(user.id), action=AuditLog.Action.UPDATE
            )
            .order_by("-at")
            .first()
        )
        assert row is not None and "password" in row.changes
        assert row.changes["password"]["new"] == "***"

    def test_update_writes_diff(self):
        unit = OrgUnit.objects.create(name="Forensics")
        unit.name = "Forensics Directorate"
        unit.save()
        row = (
            AuditLog.objects.filter(
                entity="basedata.OrgUnit",
                entity_id=str(unit.id),
                action=AuditLog.Action.UPDATE,
            )
            .order_by("-at")
            .first()
        )
        assert row is not None
        assert row.changes["name"] == {"old": "Forensics", "new": "Forensics Directorate"}
        assert "updated_at" not in row.changes  # ignored noise field

    def test_delete_writes_snapshot(self):
        unit = OrgUnit.objects.create(name="Temp Unit")
        unit_id = str(unit.id)
        unit.delete()
        row = AuditLog.objects.get(
            entity="basedata.OrgUnit", entity_id=unit_id, action=AuditLog.Action.DELETE
        )
        assert row.changes["old"]["name"] == "Temp Unit"

    def test_noop_save_writes_nothing(self):
        unit = OrgUnit.objects.create(name="Static Unit")
        before = AuditLog.objects.filter(entity="basedata.OrgUnit").count()
        unit.save()  # no field changed
        assert AuditLog.objects.filter(entity="basedata.OrgUnit").count() == before

    def test_last_login_only_change_is_ignored(self, django_user_model):
        user = UserFactory()
        before = AuditLog.objects.filter(entity="accounts.User").count()
        from django.utils import timezone

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        assert AuditLog.objects.filter(entity="accounts.User").count() == before

    def test_untracked_model_writes_nothing(self):
        from apps.accounts.services import log_activity
        from apps.accounts.models import UserActivityLog

        user = UserFactory()
        before = AuditLog.objects.count()
        log_activity(UserActivityLog.Action.LOGOUT, user=user)
        assert AuditLog.objects.count() == before


class TestActorAttribution:
    def test_api_mutation_records_actor_ip_and_agent(self, auth_client):
        client = auth_client("admin")
        resp = client.patch(
            f"/api/v1/users/{client.user.id}/",
            {"first_name": "Renamed"},
            format="json",
            HTTP_USER_AGENT="pytest-agent/1.0",
        )
        assert resp.status_code == 200
        row = (
            AuditLog.objects.filter(
                entity="accounts.User",
                entity_id=str(client.user.id),
                action=AuditLog.Action.UPDATE,
            )
            .order_by("-at")
            .first()
        )
        assert row is not None
        assert row.actor_id == client.user.id
        assert row.actor_username == client.user.username
        assert row.ip == "127.0.0.1"
        assert row.user_agent == "pytest-agent/1.0"
        assert row.changes["first_name"]["new"] == "Renamed"

    def test_mutation_outside_request_has_no_actor(self):
        unit = OrgUnit.objects.create(name="Shell Created")
        row = AuditLog.objects.get(entity="basedata.OrgUnit", entity_id=str(unit.id))
        assert row.actor is None
        assert row.actor_username == ""
        assert row.ip is None
