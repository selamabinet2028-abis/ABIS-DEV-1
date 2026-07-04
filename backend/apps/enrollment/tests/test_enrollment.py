"""T-007: capture pipeline — quality scoring, encrypted templates, RBAC."""

import io

import numpy as np
import pytest
from PIL import Image

from apps.audit.models import AuditLog
from apps.enrollment.models import (BiometricRecord, BiometricTemplate,
                                    Enrollment)
from apps.preprocessing import services as preprocessing
from apps.preprocessing.crypto import decrypt_bytes, encrypt_bytes

from .factories import EnrollmentFactory, StationFactory

pytestmark = pytest.mark.django_db

ENROLLMENTS = "/api/v1/enrollments/"


def image_upload(
    seed: int = 0, *, flat: bool = False, name: str | None = None
) -> io.BytesIO:
    """Deterministic test image: seeded noise scores high, flat gray scores 1."""
    if flat:
        array = np.full((128, 128), 128, dtype=np.uint8)
    else:
        array = np.random.default_rng(seed).integers(0, 255, (128, 128), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(array, mode="L").save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = name or f"capture-{seed}.png"
    return buffer


def capture(client, enrollment_id, modality, position, upload):
    return client.post(
        f"{ENROLLMENTS}{enrollment_id}/biometrics/",
        {"modality": modality, "position": position, "image": upload},
        format="multipart",
    )


class TestCrypto:
    def test_roundtrip_and_ciphertext_differs(self):
        plain = b"GRID16:" + bytes(range(256))
        cipher = encrypt_bytes(plain)
        assert cipher != plain
        assert decrypt_bytes(cipher) == plain


class TestQualityScoring:
    def test_noise_scores_high_flat_scores_low(self):
        noisy = image_upload(1).getvalue()
        flat = image_upload(flat=True).getvalue()
        assert preprocessing.quality_score(noisy) >= 4
        assert preprocessing.quality_score(flat) == 1

    def test_template_is_deterministic(self):
        data = image_upload(7).getvalue()
        assert preprocessing.extract_template(data) == preprocessing.extract_template(
            data
        )
        assert preprocessing.extract_template(data).startswith(b"GRID16:")


class TestTenPrintFlow:
    def test_full_ten_print_set(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()

        for position in map(str, range(1, 11)):
            resp = capture(
                client, enrollment.id, "finger", position, image_upload(int(position))
            )
            assert resp.status_code == 201, resp.json()
            body = resp.json()
            assert body["accepted"] is True
            assert 1 <= body["quality_score"] <= 5

        records = BiometricRecord.objects.filter(enrollment=enrollment)
        assert records.count() == 10
        assert set(records.values_list("position", flat=True)) == {
            str(n) for n in range(1, 11)
        }
        assert all(r.sha256 and r.nist_meta["width"] == 128 for r in records)

        # Every accepted record got an encrypted template.
        for record in records:
            stored = bytes(record.template.template_bytes)
            plaintext = preprocessing.extract_template(record.image.open("rb").read())
            assert stored != plaintext  # encrypted at rest
            assert decrypt_bytes(stored) == plaintext

        # Complete the session — launches the DEDUP MatchJob (T-008, eager).
        resp = client.post(f"{ENROLLMENTS}{enrollment.id}/complete/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["dedup_job_id"] is not None
        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.COMPLETED
        assert enrollment.completed_at is not None

        from apps.matching.models import MatchJob

        job = MatchJob.objects.get(id=body["dedup_job_id"])
        assert job.job_type == MatchJob.JobType.DEDUP
        assert job.status == MatchJob.Status.DONE
        assert job.candidates.count() == 0  # first enrollment of this person

    def test_low_quality_rejected_without_template(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        resp = capture(client, enrollment.id, "finger", "1", image_upload(flat=True))
        assert resp.status_code == 201
        body = resp.json()
        assert body["accepted"] is False
        assert body["quality_score"] == 1
        record = BiometricRecord.objects.get(id=body["record_id"])
        assert not BiometricTemplate.objects.filter(record=record).exists()

    def test_complete_requires_an_accepted_record(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        capture(
            client, enrollment.id, "finger", "1", image_upload(flat=True)
        )  # rejected
        resp = client.post(f"{ENROLLMENTS}{enrollment.id}/complete/")
        assert resp.status_code == 400

    def test_capture_on_completed_enrollment_rejected(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory(status=Enrollment.Status.COMPLETED)
        resp = capture(client, enrollment.id, "finger", "1", image_upload(2))
        assert resp.status_code == 400


class TestCaptureValidation:
    def test_invalid_position_for_modality(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        resp = capture(client, enrollment.id, "face", "11", image_upload(3))
        assert resp.status_code == 400
        assert "position" in resp.json()

    def test_face_positions_accepted(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        for position in ("frontal", "left_profile", "right_profile"):
            resp = capture(client, enrollment.id, "face", position, image_upload(4))
            assert resp.status_code == 201

    def test_disallowed_extension_rejected(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        upload = image_upload(5, name="capture.exe")
        resp = capture(client, enrollment.id, "finger", "2", upload)
        assert resp.status_code == 400
        assert "image" in resp.json()

    def test_non_image_bytes_rejected(self, auth_client):
        client = auth_client("operator")
        enrollment = EnrollmentFactory()
        fake = io.BytesIO(b"MZ\x90\x00 definitely not an image")
        fake.name = "capture.png"
        resp = capture(client, enrollment.id, "finger", "2", fake)
        assert resp.status_code == 400


class TestRbacAndAudit:
    def test_enrollment_create_sets_operator_and_audits(self, auth_client):
        client = auth_client("operator")
        person = EnrollmentFactory().person  # reuse a person
        station = StationFactory()
        resp = client.post(
            ENROLLMENTS,
            {"person": str(person.id), "station": str(station.id)},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["operator_username"] == client.user.username
        assert AuditLog.objects.filter(
            entity="enrollment.Enrollment",
            entity_id=resp.json()["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    @pytest.mark.parametrize(
        "role,read,write",
        [
            ("admin", 200, 201),
            ("operator", 200, 201),
            ("investigator", 200, 403),
            ("supervisor", 200, 403),
            ("auditor", 403, 403),
        ],
    )
    def test_matrix(self, auth_client, role, read, write):
        enrollment = EnrollmentFactory()
        client = auth_client(role)
        assert client.get(ENROLLMENTS).status_code == read
        resp = capture(client, enrollment.id, "finger", "1", image_upload(6))
        assert resp.status_code == write

    def test_image_download_is_audited(self, auth_client):
        operator = auth_client("operator")
        enrollment = EnrollmentFactory()
        record_id = capture(
            operator, enrollment.id, "finger", "3", image_upload(8)
        ).json()["record_id"]

        resp = auth_client("investigator").get(
            f"/api/v1/biometric-records/{record_id}/image/"
        )
        assert resp.status_code == 200
        assert AuditLog.objects.filter(
            entity="enrollment.BiometricRecord",
            entity_id=record_id,
            action=AuditLog.Action.VIEW,
        ).exists()

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(ENROLLMENTS).status_code == 401
