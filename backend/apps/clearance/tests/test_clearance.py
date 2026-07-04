"""T-014: decision endpoint, certificate issuance (PDF + QR), download."""

import json

import pytest

from apps.audit.models import AuditLog
from apps.clearance.models import Certificate
from apps.clearance.services import issue_certificate, verify_qr_payload
from apps.registration.services import Status

from .helpers import application_in_state

pytestmark = pytest.mark.django_db

APPS = "/api/v1/applications/"


@pytest.fixture
def supervisor(auth_client):
    return auth_client("supervisor")


@pytest.fixture
def operator(auth_client):
    return auth_client("operator")


class TestDecision:
    def test_approve_in_review(self, supervisor):
        application = application_in_state(Status.IN_REVIEW)
        resp = supervisor.post(
            f"{APPS}{application.id}/decision/", {"decision": "approved"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject_with_note(self, supervisor):
        application = application_in_state(Status.IN_REVIEW)
        resp = supervisor.post(
            f"{APPS}{application.id}/decision/",
            {"decision": "rejected", "note": "Pending case found"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "rejected"
        assert body["decision_note"] == "Pending case found"

    def test_decision_requires_in_review(self, supervisor):
        application = application_in_state(Status.PAID)
        resp = supervisor.post(
            f"{APPS}{application.id}/decision/", {"decision": "approved"}, format="json"
        )
        assert resp.status_code == 400

    def test_operator_cannot_decide(self, operator):
        application = application_in_state(Status.IN_REVIEW)
        resp = operator.post(
            f"{APPS}{application.id}/decision/", {"decision": "approved"}, format="json"
        )
        assert resp.status_code == 403


class TestAdvanceEndpoints:
    def test_paid_to_review_chain(self, operator):
        application = application_in_state(Status.PAID)
        r1 = operator.post(f"{APPS}{application.id}/biometrics-captured/")
        assert r1.status_code == 200
        assert r1.json()["status"] == "biometrics_captured"
        r2 = operator.post(f"{APPS}{application.id}/to-review/")
        assert r2.status_code == 200
        assert r2.json()["status"] == "in_review"

    def test_advance_guards_illegal_jump(self, operator):
        application = application_in_state(Status.SUBMITTED)
        resp = operator.post(f"{APPS}{application.id}/biometrics-captured/")
        assert resp.status_code == 400


class TestIssuance:
    def test_issue_certificate_full_flow(self, operator):
        application = application_in_state(Status.APPROVED)
        resp = operator.post(f"{APPS}{application.id}/issue-certificate/")
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["certificate_no"].startswith("CERT-")
        assert body["verification_no"].startswith("EFP-")
        assert body["effective_status"] == "valid"

        certificate = Certificate.objects.get(id=body["id"])
        pdf = certificate.pdf_file.open("rb").read()
        assert pdf.startswith(b"%PDF")  # real PDF
        assert len(pdf) > 1000

        application.refresh_from_db()
        assert application.status == Status.CERTIFICATE_ISSUED
        assert AuditLog.objects.filter(
            entity="clearance.Certificate",
            entity_id=body["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    def test_qr_payload_parses_and_signature_verifies(self, db):
        application = application_in_state(Status.APPROVED)
        certificate = issue_certificate(application)

        data = json.loads(certificate.qr_payload)
        assert data["no"] == certificate.verification_no
        assert data["name"] == certificate.person.full_name
        ok, number = verify_qr_payload(certificate.qr_payload)
        assert ok is True
        assert number == certificate.verification_no

        # Tampering breaks the signature.
        tampered = dict(data, name="Someone Else")
        ok_tampered, _ = verify_qr_payload(json.dumps(tampered))
        assert ok_tampered is False

    def test_reissue_rejected(self, operator):
        application = application_in_state(Status.APPROVED)
        assert (
            operator.post(f"{APPS}{application.id}/issue-certificate/").status_code
            == 201
        )
        assert (
            operator.post(f"{APPS}{application.id}/issue-certificate/").status_code
            == 400
        )

    def test_issue_requires_approved(self, operator):
        application = application_in_state(Status.IN_REVIEW)
        resp = operator.post(f"{APPS}{application.id}/issue-certificate/")
        assert resp.status_code == 400

    def test_download_is_audited(self, operator, db):
        application = application_in_state(Status.APPROVED)
        certificate = issue_certificate(application)
        resp = operator.get(f"/api/v1/certificates/{certificate.id}/download/")
        assert resp.status_code == 200
        assert AuditLog.objects.filter(
            entity="clearance.Certificate",
            entity_id=str(certificate.id),
            action=AuditLog.Action.VIEW,
        ).exists()

    def test_investigator_cannot_issue(self, auth_client):
        application = application_in_state(Status.APPROVED)
        resp = auth_client("investigator").post(
            f"{APPS}{application.id}/issue-certificate/"
        )
        assert resp.status_code == 403
