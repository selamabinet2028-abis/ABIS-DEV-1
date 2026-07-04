"""T-008: identify/verify/jobs/decision endpoints + RBAC (eager Celery)."""

import pytest

from apps.matching.models import MatchCandidate, MatchJob

from .helpers import enroll_person

pytestmark = pytest.mark.django_db

IDENTIFY = "/api/v1/match/identify/"
VERIFY = "/api/v1/match/verify/"
JOBS = "/api/v1/match/jobs/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


class TestIdentify:
    def test_identify_returns_ranked_candidates(self, investigator):
        # Person A enrolled earlier with image 500; probe is a fresh record
        # of the same image (new enrollment of person B — realistic 1:N probe).
        _, record_a = enroll_person(500)
        enroll_person(501)  # unrelated person in the gallery
        _, probe_record = enroll_person(500)

        resp = investigator.post(
            IDENTIFY,
            {"probe": str(probe_record.id), "job_type": "TP-TP"},
            format="json",
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        detail = investigator.get(f"{JOBS}{job_id}/")
        assert detail.status_code == 200
        body = detail.json()
        assert body["status"] == "done"
        candidates = body["candidates"]
        assert candidates, "expected at least the duplicate record"
        assert candidates[0]["rank"] == 1
        assert candidates[0]["score"] == 100.0
        assert candidates[0]["record"] == str(record_a.id)
        scores = [c["score"] for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_identify_threshold_filters_gallery(self, investigator):
        enroll_person(510)
        _, probe_record = enroll_person(511)  # nothing matches at high threshold

        resp = investigator.post(
            IDENTIFY,
            {"probe": str(probe_record.id), "job_type": "TP-TP", "threshold": 99.0},
            format="json",
        )
        job_id = resp.json()["job_id"]
        body = investigator.get(f"{JOBS}{job_id}/").json()
        assert body["status"] == "done"
        assert body["candidates"] == []

    def test_face_1n_requires_face_record(self, investigator):
        _, finger_record = enroll_person(520)
        resp = investigator.post(
            IDENTIFY,
            {"probe": str(finger_record.id), "job_type": "FACE-1N"},
            format="json",
        )
        assert resp.status_code == 400
        assert "probe" in resp.json()

    def test_face_1n_matches_faces(self, investigator):
        _, face_a = enroll_person(530, modality="face", position="frontal")
        _, probe = enroll_person(530, modality="face", position="frontal")
        resp = investigator.post(
            IDENTIFY, {"probe": str(probe.id), "job_type": "FACE-1N"}, format="json"
        )
        job_id = resp.json()["job_id"]
        body = investigator.get(f"{JOBS}{job_id}/").json()
        assert body["candidates"][0]["record"] == str(face_a.id)

    def test_latent_job_types_rejected_until_t009(self, investigator):
        _, record = enroll_person(540)
        for job_type in ("LT-TP", "LT-LT"):
            resp = investigator.post(
                IDENTIFY, {"probe": str(record.id), "job_type": job_type}, format="json"
            )
            assert resp.status_code == 400

    def test_identify_unknown_record_404(self, investigator):
        resp = investigator.post(
            IDENTIFY,
            {"probe": "00000000-0000-0000-0000-000000000000", "job_type": "TP-TP"},
            format="json",
        )
        assert resp.status_code == 404


class TestVerify:
    def test_verify_same_biometrics_matches(self, investigator):
        enrollment, record = enroll_person(600)
        _, new_record = enroll_person(600, person=enrollment.person, position="2")

        resp = investigator.post(
            VERIFY,
            {"person_id": str(enrollment.person_id), "record_id": str(new_record.id)},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["match"] is True
        assert body["score"] == 100.0
        job = MatchJob.objects.get(id=body["job_id"])
        assert job.job_type == MatchJob.JobType.VERIFY
        assert job.status == MatchJob.Status.DONE

    def test_verify_different_person_no_match(self, investigator):
        enrollment_a, _ = enroll_person(610)
        _, record_b = enroll_person(611)

        resp = investigator.post(
            VERIFY,
            {"person_id": str(enrollment_a.person_id), "record_id": str(record_b.id)},
            format="json",
        )
        body = resp.json()
        assert body["match"] is False
        assert body["score"] < 80.0


class TestDecision:
    def _make_candidate(self, investigator) -> str:
        _, record_a = enroll_person(700)
        _, probe = enroll_person(700)
        resp = investigator.post(
            IDENTIFY, {"probe": str(probe.id), "job_type": "TP-TP"}, format="json"
        )
        body = investigator.get(f"{JOBS}{resp.json()['job_id']}/").json()
        return body["candidates"][0]["id"]

    def test_investigator_records_hit(self, investigator):
        candidate_id = self._make_candidate(investigator)
        resp = investigator.post(
            f"/api/v1/match/candidates/{candidate_id}/decision/",
            {"decision": "hit"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "hit"
        assert body["verified_by_username"] == investigator.user.username
        assert body["decided_at"] is not None

    def test_invalid_decision_rejected(self, investigator):
        candidate_id = self._make_candidate(investigator)
        resp = investigator.post(
            f"/api/v1/match/candidates/{candidate_id}/decision/",
            {"decision": "undecided"},
            format="json",
        )
        assert resp.status_code == 400

    def test_supervisor_cannot_decide(self, investigator, auth_client):
        candidate_id = self._make_candidate(investigator)
        resp = auth_client("supervisor").post(
            f"/api/v1/match/candidates/{candidate_id}/decision/",
            {"decision": "hit"},
            format="json",
        )
        assert resp.status_code == 403
        assert MatchCandidate.objects.get(id=candidate_id).decision == "undecided"


class TestRbac:
    @pytest.mark.parametrize(
        "role,expected",
        [
            ("investigator", 200),
            ("supervisor", 200),
            ("admin", 200),
            ("operator", 403),
            ("auditor", 403),
        ],
    )
    def test_jobs_list(self, auth_client, role, expected):
        assert auth_client(role).get(JOBS).status_code == expected

    def test_operator_cannot_identify(self, auth_client):
        _, record = enroll_person(800)
        resp = auth_client("operator").post(
            IDENTIFY, {"probe": str(record.id), "job_type": "TP-TP"}, format="json"
        )
        assert resp.status_code == 403

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(JOBS).status_code == 401
