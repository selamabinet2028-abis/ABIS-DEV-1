"""T-011: alerts fire on DONE match jobs hitting watchlisted persons."""

import pytest

from apps.enrollment.services import complete_enrollment
from apps.matching.tests.helpers import enroll_person
from apps.watchlist.models import WatchlistAlert

from .factories import WatchlistEntryFactory

pytestmark = pytest.mark.django_db

ALERTS = "/api/v1/watchlist-alerts/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


def identify(client, record):
    resp = client.post(
        "/api/v1/match/identify/",
        {"probe": str(record.id), "job_type": "TP-TP"},
        format="json",
    )
    assert resp.status_code == 202
    return resp.json()["job_id"]


class TestAlertHook:
    def test_alert_fires_when_candidate_is_watchlisted(self, investigator):
        # Watchlisted person enrolled with image 12000.
        enrollment, _ = enroll_person(12000)
        entry = WatchlistEntryFactory(person=enrollment.person, severity="high")

        # A new probe with the same biometrics → candidate → alert.
        _, probe_record = enroll_person(12000)
        job_id = identify(investigator, probe_record)

        alert = WatchlistAlert.objects.get(entry=entry, trigger_job_id=job_id)
        assert alert.score == 100.0
        assert enrollment.person.full_name in alert.message
        assert alert.acknowledged is False

    def test_dedup_job_also_triggers_alert(self, investigator):
        enrollment, _ = enroll_person(12100)
        entry = WatchlistEntryFactory(person=enrollment.person)

        duplicate_enrollment, _ = enroll_person(12100)  # same biometrics, new person
        result = complete_enrollment(duplicate_enrollment)

        assert WatchlistAlert.objects.filter(
            entry=entry, trigger_job_id=result["dedup_job_id"]
        ).exists()

    def test_no_alert_for_inactive_entry_or_list(self, investigator):
        enrollment_a, _ = enroll_person(12200)
        WatchlistEntryFactory(person=enrollment_a.person, active=False)

        enrollment_b, _ = enroll_person(12201)
        WatchlistEntryFactory(person=enrollment_b.person, watchlist__is_active=False)

        _, probe_a = enroll_person(12200)
        _, probe_b = enroll_person(12201)
        identify(investigator, probe_a)
        identify(investigator, probe_b)

        assert WatchlistAlert.objects.count() == 0

    def test_no_duplicate_alert_for_same_entry_and_job(self, investigator):
        enrollment, _ = enroll_person(12300)
        entry = WatchlistEntryFactory(person=enrollment.person)
        _, probe = enroll_person(12300)
        job_id = identify(investigator, probe)

        from apps.matching.models import MatchJob
        from apps.watchlist.services import create_alerts_for_job

        job = MatchJob.objects.get(id=job_id)
        assert create_alerts_for_job(job) == []  # idempotent second pass
        assert WatchlistAlert.objects.filter(entry=entry).count() == 1

    def test_unmatched_search_creates_no_alert(self, investigator):
        enrollment, _ = enroll_person(12400)
        WatchlistEntryFactory(person=enrollment.person)
        _, probe = enroll_person(12401)  # unrelated biometrics
        identify(investigator, probe)
        assert WatchlistAlert.objects.count() == 0

    def test_alert_pushed_to_channels_group(self, investigator, monkeypatch):
        sent = []

        class DummyLayer:
            async def group_send(self, group, message):
                sent.append((group, message))

        monkeypatch.setattr(
            "apps.watchlist.services.get_channel_layer", lambda: DummyLayer()
        )

        enrollment, _ = enroll_person(12500)
        WatchlistEntryFactory(person=enrollment.person)
        _, probe = enroll_person(12500)
        identify(investigator, probe)

        assert len(sent) == 1
        group, message = sent[0]
        assert group == "alerts"
        assert message["type"] == "alert.created"
        assert message["alert"]["person_no"] == enrollment.person.person_no


class TestAlertEndpoints:
    def _make_alert(self, investigator) -> str:
        enrollment, _ = enroll_person(12600)
        WatchlistEntryFactory(person=enrollment.person)
        _, probe = enroll_person(12600)
        identify(investigator, probe)
        return str(WatchlistAlert.objects.get().id)

    def test_list_filter_unacknowledged(self, investigator):
        alert_id = self._make_alert(investigator)
        resp = investigator.get(ALERTS, {"acknowledged": "false"})
        assert resp.status_code == 200
        assert [a["id"] for a in resp.json()["results"]] == [alert_id]

    def test_ack_sets_fields_and_is_idempotent(self, investigator):
        alert_id = self._make_alert(investigator)
        resp = investigator.post(f"{ALERTS}{alert_id}/ack/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["acknowledged"] is True
        assert body["acknowledged_by_username"] == investigator.user.username
        first_ack_at = body["acknowledged_at"]

        again = investigator.post(f"{ALERTS}{alert_id}/ack/").json()
        assert again["acknowledged_at"] == first_ack_at  # unchanged

        assert investigator.get(ALERTS, {"acknowledged": "false"}).json()["count"] == 0

    def test_operator_cannot_see_alerts(self, auth_client):
        assert auth_client("operator").get(ALERTS).status_code == 403
