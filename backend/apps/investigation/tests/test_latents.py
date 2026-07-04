"""T-009: latent upload, enhance ops + history, minutiae, audited downloads."""

import io

import pytest

from apps.audit.models import AuditLog
from apps.investigation.models import LatentPrint
from apps.matching.tests.helpers import png_bytes

from .factories import CaseFactory, LatentFactory

pytestmark = pytest.mark.django_db

CASES = "/api/v1/cases/"
LATENTS = "/api/v1/latents/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


def upload_latent(client, case, seed=9100, modality="finger"):
    image = io.BytesIO(png_bytes(seed))
    image.name = "scene-latent.png"
    return client.post(
        f"{CASES}{case.id}/latents/",
        {"modality": modality, "image": image, "notes": "lifted from door handle"},
        format="multipart",
    )


class TestLatentUpload:
    def test_upload_creates_latent_with_sha256(self, investigator):
        case = CaseFactory()
        resp = upload_latent(investigator, case)
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["case_no"] == case.case_no
        assert len(body["sha256"]) == 64
        assert body["has_enhanced"] is False
        assert AuditLog.objects.filter(
            entity="investigation.LatentPrint",
            entity_id=body["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    def test_upload_rejects_bad_extension(self, investigator):
        case = CaseFactory()
        bad = io.BytesIO(b"not an image")
        bad.name = "latent.exe"
        resp = investigator.post(
            f"{CASES}{case.id}/latents/",
            {"modality": "finger", "image": bad},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_supervisor_cannot_upload(self, auth_client):
        case = CaseFactory()
        resp = upload_latent(auth_client("supervisor"), case)
        assert resp.status_code == 403


class TestEnhance:
    def test_operations_produce_enhanced_image_and_history(self, investigator):
        latent = LatentFactory()
        resp = investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {
                "operations": [
                    {"op": "contrast", "factor": 1.8},
                    {"op": "invert"},
                    {"op": "rotate", "angle": 90},
                    {"op": "crop", "box": [0, 0, 64, 64]},
                ]
            },
            format="json",
        )
        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["has_enhanced"] is True
        assert len(body["editor_history"]) == 1
        entry = body["editor_history"][0]
        assert entry["action"] == "enhance"
        assert entry["by"] == investigator.user.username
        assert len(entry["operations"]) == 4
        assert len(entry["result_sha256"]) == 64

        # Second enhancement appends to history (works on the enhanced image).
        resp2 = investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {"operations": [{"op": "invert"}]},
            format="json",
        )
        assert len(resp2.json()["editor_history"]) == 2

    def test_unknown_operation_rejected(self, investigator):
        latent = LatentFactory()
        resp = investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {"operations": [{"op": "sharpen"}]},
            format="json",
        )
        assert resp.status_code == 400

    def test_crop_out_of_bounds_rejected(self, investigator):
        latent = LatentFactory()
        resp = investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {"operations": [{"op": "crop", "box": [0, 0, 4096, 4096]}]},
            format="json",
        )
        assert resp.status_code == 400
        assert "operations" in resp.json()

    def test_contrast_requires_factor(self, investigator):
        latent = LatentFactory()
        resp = investigator.post(
            f"{LATENTS}{latent.id}/enhance/",
            {"operations": [{"op": "contrast"}]},
            format="json",
        )
        assert resp.status_code == 400


class TestMinutiae:
    def test_auto_extract_is_deterministic(self, investigator):
        latent = LatentFactory()
        first = investigator.post(f"{LATENTS}{latent.id}/minutiae/extract/").json()
        second = investigator.post(f"{LATENTS}{latent.id}/minutiae/extract/").json()
        assert first["minutiae"] == second["minutiae"]
        assert first["minutiae_count"] > 0
        point = first["minutiae"][0]
        assert set(point) == {"x", "y", "angle", "type", "quality"}
        assert point["type"] in {"ridge_ending", "bifurcation"}

    def test_manual_edit_replaces_set_and_logs_history(self, investigator):
        latent = LatentFactory()
        payload = {
            "minutiae": [
                {
                    "x": 10,
                    "y": 20,
                    "angle": 45.0,
                    "type": "ridge_ending",
                    "quality": 0.9,
                },
                {"x": 30, "y": 40, "angle": 180.0, "type": "bifurcation"},
            ]
        }
        resp = investigator.patch(
            f"{LATENTS}{latent.id}/minutiae/", payload, format="json"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["minutiae_count"] == 2
        assert body["editor_history"][-1]["action"] == "minutiae_manual_edit"

    def test_manual_edit_validates_schema(self, investigator):
        latent = LatentFactory()
        resp = investigator.patch(
            f"{LATENTS}{latent.id}/minutiae/",
            {"minutiae": [{"x": -5, "y": 0, "angle": 999, "type": "loop"}]},
            format="json",
        )
        assert resp.status_code == 400


class TestDownloads:
    def test_image_download_audited(self, investigator):
        latent = LatentFactory()
        resp = investigator.get(f"{LATENTS}{latent.id}/image/")
        assert resp.status_code == 200
        assert AuditLog.objects.filter(
            entity="investigation.LatentPrint",
            entity_id=str(latent.id),
            action=AuditLog.Action.VIEW,
        ).exists()

    def test_enhanced_image_404_before_enhancement(self, investigator):
        latent = LatentFactory()
        resp = investigator.get(f"{LATENTS}{latent.id}/enhanced-image/")
        assert resp.status_code == 404

    def test_latent_detail_hides_nothing_but_lists_history(self, investigator):
        latent = LatentFactory()
        body = investigator.get(f"{LATENTS}{latent.id}/").json()
        assert body["editor_history"] == []
        assert body["modality"] == LatentPrint.Modality.FINGER
