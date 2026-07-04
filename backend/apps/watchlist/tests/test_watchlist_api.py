"""T-011: watchlist/entry CRUD + RBAC."""

import pytest

from apps.basedata.tests.factories import PersonFactory
from apps.watchlist.models import WatchlistEntry

from .factories import WatchlistEntryFactory, WatchlistFactory

pytestmark = pytest.mark.django_db

LISTS = "/api/v1/watchlists/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


class TestWatchlistCrud:
    def test_create_list_and_add_entry(self, investigator):
        resp = investigator.post(
            LISTS,
            {"name": "High-priority criminals", "list_type": "criminal"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        list_id = resp.json()["id"]
        assert resp.json()["created_by_username"] == investigator.user.username

        person = PersonFactory()
        entry_resp = investigator.post(
            f"{LISTS}{list_id}/entries/",
            {"person": str(person.id), "reason": "Escaped convict", "severity": "high"},
            format="json",
        )
        assert entry_resp.status_code == 201
        assert entry_resp.json()["person_no"] == person.person_no

        listed = investigator.get(f"{LISTS}{list_id}/entries/").json()
        assert len(listed) == 1

    def test_duplicate_person_on_list_rejected(self, investigator):
        entry = WatchlistEntryFactory()
        resp = investigator.post(
            f"{LISTS}{entry.watchlist_id}/entries/",
            {"person": str(entry.person_id), "reason": "again"},
            format="json",
        )
        assert resp.status_code == 400

    def test_patch_entry_severity(self, investigator):
        entry = WatchlistEntryFactory()
        resp = investigator.patch(
            f"{LISTS}{entry.watchlist_id}/entries/{entry.id}/",
            {"severity": "critical"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["severity"] == "critical"

    def test_delete_entry_deactivates(self, investigator):
        entry = WatchlistEntryFactory()
        resp = investigator.delete(f"{LISTS}{entry.watchlist_id}/entries/{entry.id}/")
        assert resp.status_code == 204
        entry.refresh_from_db()
        assert entry.active is False
        assert WatchlistEntry.objects.filter(id=entry.id).exists()

    def test_no_hard_delete_of_lists(self, investigator):
        watchlist = WatchlistFactory()
        assert investigator.delete(f"{LISTS}{watchlist.id}/").status_code == 405

    @pytest.mark.parametrize(
        "role,read,write",
        [
            ("admin", 200, 201),
            ("investigator", 200, 201),
            ("supervisor", 200, 201),
            ("operator", 403, 403),
            ("auditor", 403, 403),
        ],
    )
    def test_rbac_matrix(self, auth_client, role, read, write):
        client = auth_client(role)
        assert client.get(LISTS).status_code == read
        resp = client.post(
            LISTS, {"name": f"probe-{role}", "list_type": "fraud"}, format="json"
        )
        assert resp.status_code == write

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(LISTS).status_code == 401
