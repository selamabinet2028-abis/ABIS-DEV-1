"""T-010: face photo search (FACE-1N from upload) + candidate review."""

import io

import pytest

from apps.audit.models import AuditLog
from apps.matching.tests.helpers import enroll_person, png_bytes
from apps.pis.models import PhotoProbe

pytestmark = pytest.mark.django_db

SEARCH = "/api/v1/pis/search/"


def face_upload(seed: int, name: str = "probe.png") -> io.BytesIO:
    buffer = io.BytesIO(png_bytes(seed))
    buffer.name = name
    return buffer


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


class TestFaceSearch:
    def test_search_returns_candidates_from_seeded_faces(self, investigator):
        # Seeded gallery: two enrolled faces, one matching the probe photo.
        target_enrollment, target_record = enroll_person(
            11000, modality="face", position="frontal"
        )
        enroll_person(11001, modality="face", position="frontal")  # unrelated

        resp = investigator.post(
            SEARCH, {"image": face_upload(11000)}, format="multipart"
        )
        assert resp.status_code == 202, resp.json()
        body = resp.json()
        job_id, probe_id = body["job_id"], body["probe_id"]

        # Probe persisted with sha256 + audit row.
        probe = PhotoProbe.objects.get(id=probe_id)
        assert len(probe.sha256) == 64
        assert probe.uploaded_by_id == investigator.user.id
        assert AuditLog.objects.filter(
            entity="pis.PhotoProbe", entity_id=probe_id, action=AuditLog.Action.CREATE
        ).exists()

        # Candidate review endpoint: ranked, matching person on top.
        review = investigator.get(f"/api/v1/pis/jobs/{job_id}/candidates/")
        assert review.status_code == 200
        review_body = review.json()
        assert review_body["status"] == "done"
        candidates = review_body["candidates"]
        assert candidates, "expected the enrolled face to match"
        top = candidates[0]
        assert top["person"] == str(target_enrollment.person_id)
        assert top["record"] == str(target_record.id)
        assert top["score"] == 100.0
        assert top["rank"] == 1

    def test_job_detail_includes_probe_info(self, investigator):
        enroll_person(11100, modality="face", position="frontal")
        resp = investigator.post(
            SEARCH, {"image": face_upload(11100)}, format="multipart"
        )
        job_id = resp.json()["job_id"]

        detail = investigator.get(f"/api/v1/pis/jobs/{job_id}/")
        assert detail.status_code == 200
        body = detail.json()
        assert body["job_type"] == "FACE-1N"
        assert body["probe_photo_detail"]["id"] == resp.json()["probe_id"]

    def test_high_threshold_yields_no_candidates(self, investigator):
        enroll_person(11200, modality="face", position="frontal")
        resp = investigator.post(
            SEARCH,
            {"image": face_upload(11201), "threshold": 99.0},
            format="multipart",
        )
        review = investigator.get(
            f"/api/v1/pis/jobs/{resp.json()['job_id']}/candidates/"
        ).json()
        assert review["status"] == "done"
        assert review["candidates"] == []

    def test_decision_on_face_candidate(self, investigator):
        enroll_person(11300, modality="face", position="frontal")
        resp = investigator.post(
            SEARCH, {"image": face_upload(11300)}, format="multipart"
        )
        review = investigator.get(
            f"/api/v1/pis/jobs/{resp.json()['job_id']}/candidates/"
        ).json()
        candidate_id = review["candidates"][0]["id"]

        decision = investigator.post(
            f"/api/v1/match/candidates/{candidate_id}/decision/",
            {"decision": "hit"},
            format="json",
        )
        assert decision.status_code == 200
        assert decision.json()["decision"] == "hit"

    def test_probe_image_download_audited(self, investigator):
        enroll_person(11400, modality="face", position="frontal")
        resp = investigator.post(
            SEARCH, {"image": face_upload(11400)}, format="multipart"
        )
        probe_id = resp.json()["probe_id"]

        download = investigator.get(f"/api/v1/pis/probes/{probe_id}/image/")
        assert download.status_code == 200
        assert AuditLog.objects.filter(
            entity="pis.PhotoProbe", entity_id=probe_id, action=AuditLog.Action.VIEW
        ).exists()


class TestValidation:
    def test_undecodable_image_400(self, investigator):
        fake = io.BytesIO(b"MZ definitely not an image")
        fake.name = "probe.png"
        resp = investigator.post(SEARCH, {"image": fake}, format="multipart")
        assert resp.status_code == 400
        assert "image" in resp.json()
        assert not PhotoProbe.objects.exists()  # nothing persisted on failure

    def test_bad_extension_400(self, investigator):
        resp = investigator.post(
            SEARCH, {"image": face_upload(11500, name="probe.exe")}, format="multipart"
        )
        assert resp.status_code == 400

    def test_non_face_job_404_on_pis_endpoints(self, investigator):
        _, record = enroll_person(11600)  # finger enrollment
        job = investigator.post(
            "/api/v1/match/identify/",
            {"probe": str(record.id), "job_type": "TP-TP"},
            format="json",
        ).json()["job_id"]
        assert investigator.get(f"/api/v1/pis/jobs/{job}/").status_code == 404


class TestRbac:
    def test_supervisor_can_search(self, auth_client):
        enroll_person(11700, modality="face", position="frontal")
        resp = auth_client("supervisor").post(
            SEARCH, {"image": face_upload(11700)}, format="multipart"
        )
        assert resp.status_code == 202

    @pytest.mark.parametrize("role", ["operator", "auditor"])
    def test_forbidden_roles(self, auth_client, role):
        resp = auth_client(role).post(
            SEARCH, {"image": face_upload(11800)}, format="multipart"
        )
        assert resp.status_code == 403

    def test_anonymous_401(self, api_client, db):
        resp = api_client.post(
            SEARCH, {"image": face_upload(11900)}, format="multipart"
        )
        assert resp.status_code == 401
