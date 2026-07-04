"""T-012: application CRUD, document upload, status machine enforcement."""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditLog
from apps.registration.models import ClearanceApplication
from apps.registration.services import Status, mark_paid, submit, transition

from .factories import ApplicationFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/applications/"


@pytest.fixture
def operator(auth_client):
    return auth_client("operator")


def pdf_upload(name="id-card.pdf") -> io.BytesIO:
    buffer = io.BytesIO(b"%PDF-1.4 scanned id document")
    buffer.name = name
    return buffer


def with_document(application: ClearanceApplication) -> ClearanceApplication:
    application.id_document = SimpleUploadedFile("id.pdf", b"%PDF-1.4 x")
    application.save(update_fields=["id_document"])
    return application


class TestApplicationCrud:
    def test_create_generates_tracking_no(self, operator):
        person = ApplicationFactory().person  # reuse a person
        resp = operator.post(
            URL, {"person": str(person.id), "purpose": "visa"}, format="json"
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["tracking_no"].startswith("PCC-")
        assert body["status"] == "draft"
        assert body["created_by_username"] == operator.user.username
        assert AuditLog.objects.filter(
            entity="registration.ClearanceApplication",
            entity_id=body["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    def test_tracking_numbers_unique(self, db):
        a, b = ApplicationFactory(), ApplicationFactory()
        assert a.tracking_no != b.tracking_no

    def test_search_by_tracking_no_and_status_filter(self, operator):
        application = ApplicationFactory()
        ApplicationFactory()
        results = operator.get(URL, {"search": application.tracking_no}).json()[
            "results"
        ]
        assert [r["id"] for r in results] == [str(application.id)]
        drafts = operator.get(URL, {"status": "draft"}).json()["count"]
        assert drafts == 2

    def test_patch_cannot_change_status(self, operator):
        application = ApplicationFactory()
        resp = operator.patch(
            f"{URL}{application.id}/", {"status": "approved"}, format="json"
        )
        assert resp.status_code == 200
        application.refresh_from_db()
        assert application.status == Status.DRAFT  # read-only field ignored

    @pytest.mark.parametrize(
        "role,read,write",
        [
            ("admin", 200, 201),
            ("operator", 200, 201),
            ("supervisor", 200, 201),
            ("investigator", 403, 403),
            ("auditor", 403, 403),
        ],
    )
    def test_rbac_matrix(self, auth_client, role, read, write):
        person = ApplicationFactory().person
        client = auth_client(role)
        assert client.get(URL).status_code == read
        resp = client.post(
            URL, {"person": str(person.id), "purpose": "x"}, format="json"
        )
        assert resp.status_code == write

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(URL).status_code == 401


class TestDocumentUpload:
    def test_upload_pdf(self, operator):
        application = ApplicationFactory()
        resp = operator.post(
            f"{URL}{application.id}/document/",
            {"file": pdf_upload()},
            format="multipart",
        )
        assert resp.status_code == 200
        assert resp.json()["has_id_document"] is True

    def test_upload_rejects_bad_extension(self, operator):
        application = ApplicationFactory()
        resp = operator.post(
            f"{URL}{application.id}/document/",
            {"file": pdf_upload(name="malware.exe")},
            format="multipart",
        )
        assert resp.status_code == 400


class TestStatusMachine:
    def test_submit_requires_document(self, operator):
        application = ApplicationFactory()
        resp = operator.post(f"{URL}{application.id}/submit/")
        assert resp.status_code == 400

    def test_submit_endpoint_happy_path(self, operator):
        application = with_document(ApplicationFactory())
        resp = operator.post(f"{URL}{application.id}/submit/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "submitted"
        assert body["submitted_at"] is not None

    def test_full_legal_chain(self, db):
        application = with_document(ApplicationFactory())
        submit(application)
        mark_paid(application)
        transition(application, Status.BIOMETRICS_CAPTURED)
        transition(application, Status.IN_REVIEW)
        transition(application, Status.APPROVED)
        transition(application, Status.CERTIFICATE_ISSUED)
        application.refresh_from_db()
        assert application.status == Status.CERTIFICATE_ISSUED

    def test_rejection_path(self, db):
        application = with_document(ApplicationFactory())
        submit(application)
        mark_paid(application)
        transition(application, Status.BIOMETRICS_CAPTURED)
        transition(application, Status.IN_REVIEW)
        transition(application, Status.REJECTED, note="Incomplete records")
        application.refresh_from_db()
        assert application.status == Status.REJECTED
        assert application.decision_note == "Incomplete records"

    @pytest.mark.parametrize(
        "start,target",
        [
            (Status.DRAFT, Status.APPROVED),
            (Status.DRAFT, Status.PAID),
            (Status.SUBMITTED, Status.APPROVED),
            (Status.REJECTED, Status.IN_REVIEW),
            (Status.CERTIFICATE_ISSUED, Status.DRAFT),
            (Status.APPROVED, Status.REJECTED),
        ],
    )
    def test_illegal_transitions_raise(self, db, start, target):
        application = ApplicationFactory(status=start)
        with pytest.raises(ValidationError):
            transition(application, target)
        application.refresh_from_db()
        assert application.status == start

    def test_double_submit_rejected(self, operator):
        application = with_document(ApplicationFactory())
        assert operator.post(f"{URL}{application.id}/submit/").status_code == 200
        assert operator.post(f"{URL}{application.id}/submit/").status_code == 400
