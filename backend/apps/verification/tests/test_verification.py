"""T-014: public verify (masked), QR verify, institutional API-key verify."""

import datetime
import json

import pytest
from django.utils import timezone

from apps.apimgmt.services import create_credential
from apps.clearance.models import Certificate
from apps.clearance.services import issue_certificate
from apps.clearance.tests.helpers import application_in_state
from apps.registration.services import Status
from apps.verification.models import VerificationEvent
from apps.verification.services import mask_name

pytestmark = pytest.mark.django_db

QR_URL = "/api/v1/public/verify/qr/"
API_URL = "/api/v1/verify/api/"


def issued_certificate() -> Certificate:
    return issue_certificate(application_in_state(Status.APPROVED))


def portal_url(number: str) -> str:
    return f"/api/v1/public/verify/{number}/"


class TestMasking:
    def test_mask_name(self):
        assert mask_name("Kebede Alemu Tesfaye") == "Kebede A. T."
        assert mask_name("Selam") == "Selam"
        assert mask_name("") == ""


class TestPublicPortal:
    def test_issued_cert_verifies_valid_and_masked(self, api_client):
        certificate = issued_certificate()
        resp = api_client.get(portal_url(certificate.verification_no))
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["status"] == "valid"
        assert body["holder_name_masked"] == mask_name(certificate.person.full_name)
        assert certificate.person.full_name != body["holder_name_masked"]

        event = VerificationEvent.objects.get()
        assert event.channel == VerificationEvent.Channel.PORTAL
        assert event.result == VerificationEvent.Result.VALID
        assert event.certificate_id == certificate.id
        assert event.verifier_ip == "127.0.0.1"

    def test_unknown_number_invalid(self, api_client, db):
        resp = api_client.get(portal_url("EFP-DOESNOTEXIST"))
        assert resp.status_code == 200
        assert resp.json() == {"valid": False, "status": "invalid"}
        event = VerificationEvent.objects.get()
        assert event.result == VerificationEvent.Result.INVALID
        assert event.certificate is None

    def test_revoked_certificate(self, api_client):
        certificate = issued_certificate()
        certificate.status = Certificate.Status.REVOKED
        certificate.save(update_fields=["status"])
        body = api_client.get(portal_url(certificate.verification_no)).json()
        assert body["valid"] is False
        assert body["status"] == "revoked"

    def test_expired_certificate(self, api_client):
        certificate = issued_certificate()
        certificate.expires_at = timezone.now() - datetime.timedelta(days=1)
        certificate.save(update_fields=["expires_at"])
        body = api_client.get(portal_url(certificate.verification_no)).json()
        assert body["valid"] is False
        assert body["status"] == "expired"


class TestQrVerify:
    def test_valid_qr_payload(self, api_client):
        certificate = issued_certificate()
        resp = api_client.post(
            QR_URL, {"qr_payload": certificate.qr_payload}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True
        assert VerificationEvent.objects.get().channel == VerificationEvent.Channel.QR

    def test_tampered_signature_invalid(self, api_client):
        certificate = issued_certificate()
        data = json.loads(certificate.qr_payload)
        data["name"] = "Forged Name"
        resp = api_client.post(QR_URL, {"qr_payload": json.dumps(data)}, format="json")
        assert resp.status_code == 200
        assert resp.json() == {"valid": False, "status": "invalid"}

    def test_malformed_payload_400(self, api_client, db):
        resp = api_client.post(QR_URL, {"qr_payload": "not-json"}, format="json")
        assert resp.status_code == 400

    def test_missing_payload_400(self, api_client, db):
        assert api_client.post(QR_URL, {}, format="json").status_code == 400


class TestInstitutionalApi:
    def test_full_detail_with_valid_key(self, api_client):
        certificate = issued_certificate()
        credential, raw_key = create_credential(name="Ministry of Justice")
        resp = api_client.post(
            API_URL,
            {"verification_no": certificate.verification_no},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["holder_name"] == certificate.person.full_name  # unmasked
        assert body["person_no"] == certificate.person.person_no
        assert body["certificate_no"] == certificate.certificate_no

        event = VerificationEvent.objects.get()
        assert event.channel == VerificationEvent.Channel.API
        assert event.api_credential_id == credential.id

    def test_wrong_key_401(self, api_client):
        certificate = issued_certificate()
        create_credential(name="MoJ")
        resp = api_client.post(
            API_URL,
            {"verification_no": certificate.verification_no},
            format="json",
            HTTP_X_API_KEY="12345678.wrong-secret",
        )
        assert resp.status_code == 401

    def test_inactive_credential_401(self, api_client):
        certificate = issued_certificate()
        credential, raw_key = create_credential(name="MoJ")
        credential.is_active = False
        credential.save(update_fields=["is_active"])
        resp = api_client.post(
            API_URL,
            {"verification_no": certificate.verification_no},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        assert resp.status_code == 401

    def test_missing_key_401(self, api_client, db):
        resp = api_client.post(API_URL, {"verification_no": "EFP-X"}, format="json")
        assert resp.status_code == 401

    def test_unknown_number_with_valid_key(self, api_client, db):
        _, raw_key = create_credential(name="MoJ")
        resp = api_client.post(
            API_URL,
            {"verification_no": "EFP-UNKNOWN"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        assert resp.status_code == 200
        assert resp.json() == {"valid": False, "status": "invalid"}
