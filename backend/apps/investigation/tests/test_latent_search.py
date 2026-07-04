"""T-009 verification: full latent workflow through search to candidate decision."""

import io

import pytest

from apps.matching.tests.helpers import enroll_person, png_bytes

from .factories import CaseFactory, LatentFactory

pytestmark = pytest.mark.django_db

CASES = "/api/v1/cases/"
LATENTS = "/api/v1/latents/"
JOBS = "/api/v1/match/jobs/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


class TestFullLatentWorkflow:
    def test_upload_enhance_minutiae_search_decide(self, investigator):
        # The "suspect" is already enrolled with image #9500.
        suspect_enrollment, suspect_record = enroll_person(9500)

        # 1. Case + latent upload (same biometric source as the suspect).
        case = CaseFactory(title="Market robbery")
        image = io.BytesIO(png_bytes(9500))
        image.name = "lifted.png"
        latent_id = investigator.post(
            f"{CASES}{case.id}/latents/",
            {"modality": "finger", "image": image},
            format="multipart",
        ).json()["id"]

        # 2. Non-destructive enhancement is recorded in history.
        resp = investigator.post(
            f"{LATENTS}{latent_id}/enhance/",
            {"operations": [{"op": "contrast", "factor": 1.0}]},
            format="json",
        )
        assert resp.status_code == 200

        # 3. Minutiae: auto-extract then manual refinement.
        assert (
            investigator.post(f"{LATENTS}{latent_id}/minutiae/extract/").status_code
            == 200
        )
        assert (
            investigator.patch(
                f"{LATENTS}{latent_id}/minutiae/",
                {"minutiae": [{"x": 1, "y": 2, "angle": 10.0, "type": "ridge_ending"}]},
                format="json",
            ).status_code
            == 200
        )

        # 4. LT-TP search → ranked candidates (eager Celery).
        resp = investigator.post(
            f"{LATENTS}{latent_id}/search/", {"job_type": "LT-TP"}, format="json"
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        job_body = investigator.get(f"{JOBS}{job_id}/").json()
        assert job_body["status"] == "done"
        assert job_body["job_type"] == "LT-TP"
        assert job_body["probe_latent"] == latent_id
        candidates = job_body["candidates"]
        assert candidates, "suspect must be found"
        top = candidates[0]
        assert top["person"] == str(suspect_enrollment.person_id)
        assert top["record"] == str(suspect_record.id)
        assert top["rank"] == 1

        # 5. Human decision closes the loop.
        decision = investigator.post(
            f"/api/v1/match/candidates/{top['id']}/decision/",
            {"decision": "hit"},
            format="json",
        )
        assert decision.status_code == 200
        assert decision.json()["decision"] == "hit"
        assert decision.json()["verified_by_username"] == investigator.user.username

    def test_lt_lt_finds_matching_latent_in_other_case(self, investigator):
        latent_a = LatentFactory(image_seed=9600)
        latent_b = LatentFactory(image_seed=9600)  # same source, different case

        resp = investigator.post(
            f"{LATENTS}{latent_b.id}/search/", {"job_type": "LT-LT"}, format="json"
        )
        job_id = resp.json()["job_id"]
        body = investigator.get(f"{JOBS}{job_id}/").json()
        assert body["status"] == "done"
        candidates = body["candidates"]
        assert len(candidates) == 1
        assert candidates[0]["latent"] == str(latent_a.id)
        assert candidates[0]["latent_case_no"] == latent_a.case.case_no
        assert candidates[0]["person"] is None  # latent hits carry no identity

    def test_tp_lt_finds_unsolved_latent(self, investigator):
        latent = LatentFactory(image_seed=9700)
        _, probe_record = enroll_person(9700)

        resp = investigator.post(
            "/api/v1/match/identify/",
            {"probe": str(probe_record.id), "job_type": "TP-LT"},
            format="json",
        )
        assert resp.status_code == 202
        body = investigator.get(f"{JOBS}{resp.json()['job_id']}/").json()
        assert body["status"] == "done"
        assert body["candidates"][0]["latent"] == str(latent.id)

    def test_search_respects_threshold(self, investigator):
        LatentFactory(image_seed=9800)
        latent = LatentFactory(image_seed=9801)  # unrelated

        resp = investigator.post(
            f"{LATENTS}{latent.id}/search/",
            {"job_type": "LT-LT", "threshold": 99.0},
            format="json",
        )
        body = investigator.get(f"{JOBS}{resp.json()['job_id']}/").json()
        assert body["status"] == "done"
        assert body["candidates"] == []

    def test_enhancement_changes_search_probe(self, investigator):
        """Destructive enhancement (invert) must break the match — searches use
        the working (enhanced) image."""
        enroll_person(9900)
        latent = LatentFactory(image_seed=9900)
        investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {"operations": [{"op": "invert"}]},
            format="json",
        )
        resp = investigator.post(
            f"{LATENTS}{latent.id}/search/", {"job_type": "LT-TP"}, format="json"
        )
        body = investigator.get(f"{JOBS}{resp.json()['job_id']}/").json()
        assert body["status"] == "done"
        assert body["candidates"] == []  # inverted probe no longer matches

    def test_operator_cannot_launch_latent_search(self, auth_client):
        latent = LatentFactory(image_seed=9950)
        resp = auth_client("operator").post(
            f"{LATENTS}{latent.id}/search/", {"job_type": "LT-TP"}, format="json"
        )
        assert resp.status_code == 403
