"""T-015: status triggers enqueue SMS rows; outbox/templates endpoints."""

import hashlib
import hmac
import json

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.notifications.models import SmsMessage, SmsTemplate
from apps.payments.services import initiate_payment
from apps.registration.services import Status, submit
from apps.registration.tests.factories import ApplicationFactory

pytestmark = pytest.mark.django_db

PHONE = "0911223344"


def application_with_phone(phone: str = PHONE):
    application = ApplicationFactory(contact_phone=phone)
    application.id_document = SimpleUploadedFile("id.pdf", b"%PDF-1.4 x")
    application.save(update_fields=["id_document"])
    return application


class TestStatusTriggers:
    def test_submit_enqueues_sms_row(self, db):
        application = application_with_phone()
        submit(application)

        message = SmsMessage.objects.get()
        assert message.to_number == PHONE
        assert message.template.code == "application_submitted"
        assert application.tracking_no in message.body
        assert application.person.full_name.split()[0] in message.body
        # eager Celery + console provider → already sent
        assert message.status == SmsMessage.Status.SENT
        assert message.provider_ref.startswith("console-")
        assert message.sent_at is not None

    def test_payment_webhook_enqueues_payment_received(self, db, api_client, make_user):
        application = application_with_phone()
        submit(application)
        payment, _ = initiate_payment(
            application=application, method="telebirr", user=make_user("operator")
        )
        body = json.dumps(
            {"gateway_ref": payment.gateway_ref, "status": "paid", "amount": "300.00"}
        ).encode()
        signature = hmac.new(
            settings.ABIS_PAYMENT_WEBHOOK_SECRETS["telebirr"].encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        resp = api_client.post(
            "/api/v1/payments/webhook/telebirr/",
            data=body,
            content_type="application/json",
            HTTP_X_ABIS_SIGNATURE=signature,
        )
        assert resp.status_code == 200

        message = SmsMessage.objects.filter(template__code="payment_received").get()
        payment.refresh_from_db()
        assert payment.receipt_no in message.body

    def test_certificate_issue_enqueues_ready_sms(self, db):
        from apps.clearance.services import issue_certificate
        from apps.registration.services import mark_paid, transition

        application = application_with_phone()
        submit(application)
        mark_paid(application)
        transition(application, Status.BIOMETRICS_CAPTURED)
        transition(application, Status.IN_REVIEW)
        transition(application, Status.APPROVED)
        certificate = issue_certificate(application)

        message = SmsMessage.objects.filter(template__code="certificate_ready").get()
        assert certificate.verification_no in message.body

    def test_no_phone_skips_quietly(self, db):
        application = ApplicationFactory(contact_phone="")
        application.id_document = SimpleUploadedFile("id.pdf", b"%PDF-1.4 x")
        application.save(update_fields=["id_document"])
        submit(application)
        assert SmsMessage.objects.count() == 0

    def test_inactive_template_skips(self, db):
        SmsTemplate.objects.filter(code="application_submitted").update(is_active=False)
        application = application_with_phone()
        submit(application)
        assert SmsMessage.objects.count() == 0

    def test_rejection_sends_nothing(self, db):
        from apps.registration.services import mark_paid, transition

        application = application_with_phone()
        submit(application)
        mark_paid(application)
        transition(application, Status.BIOMETRICS_CAPTURED)
        transition(application, Status.IN_REVIEW)
        before = SmsMessage.objects.count()
        transition(application, Status.REJECTED)
        assert SmsMessage.objects.count() == before  # no template for rejection


class TestEndpoints:
    def test_send_test_admin(self, auth_client):
        resp = auth_client("admin").post(
            "/api/v1/sms/send-test/",
            {"to": "0911999888", "body": "ABIS test"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "sent"
        assert body["provider_ref"].startswith("console-")

    def test_send_test_supervisor_403(self, auth_client):
        resp = auth_client("supervisor").post(
            "/api/v1/sms/send-test/", {"to": "x", "body": "y"}, format="json"
        )
        assert resp.status_code == 403  # read-only role for notifications

    def test_outbox_list_and_filter(self, auth_client, db):
        application = application_with_phone()
        submit(application)
        client = auth_client("supervisor")
        resp = client.get("/api/v1/sms/outbox/", {"status": "sent"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_outbox_operator_403(self, auth_client):
        assert auth_client("operator").get("/api/v1/sms/outbox/").status_code == 403

    def test_templates_seeded_and_admin_crud(self, auth_client):
        admin = auth_client("admin")
        listed = admin.get("/api/v1/sms/templates/").json()
        codes = {t["code"] for t in listed["results"]}
        assert {
            "application_submitted",
            "payment_received",
            "certificate_ready",
        } <= codes

        resp = admin.post(
            "/api/v1/sms/templates/",
            {"code": "custom_alert", "body": "Hello {name}"},
            format="json",
        )
        assert resp.status_code == 201

    def test_templates_supervisor_read_only(self, auth_client):
        client = auth_client("supervisor")
        assert client.get("/api/v1/sms/templates/").status_code == 200
        resp = client.post(
            "/api/v1/sms/templates/", {"code": "x", "body": "y"}, format="json"
        )
        assert resp.status_code == 403

    def test_anonymous_401(self, api_client, db):
        assert api_client.get("/api/v1/sms/outbox/").status_code == 401
