"""T-013: initiate, HMAC webhook, receipts, reconciliation."""

import hashlib
import hmac
import json

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.payments.models import Payment, ReconciliationBatch
from apps.registration.models import ClearanceApplication
from apps.registration.services import submit
from apps.registration.tests.factories import ApplicationFactory

pytestmark = pytest.mark.django_db

INITIATE = "/api/v1/payments/initiate/"


def submitted_application() -> ClearanceApplication:
    application = ApplicationFactory()
    application.id_document = SimpleUploadedFile("id.pdf", b"%PDF-1.4 x")
    application.save(update_fields=["id_document"])
    submit(application)
    return application


def sign(provider: str, body: bytes) -> str:
    secret = settings.ABIS_PAYMENT_WEBHOOK_SECRETS[provider]
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_webhook(client, provider: str, payload: dict, signature: str | None = None):
    body = json.dumps(payload).encode()
    headers = {}
    if signature is None:
        signature = sign(provider, body)
    if signature != "":
        headers["HTTP_X_ABIS_SIGNATURE"] = signature
    return client.post(
        f"/api/v1/payments/webhook/{provider}/",
        data=body,
        content_type="application/json",
        **headers,
    )


@pytest.fixture
def operator(auth_client):
    return auth_client("operator")


def initiate(client, application, method="telebirr"):
    return client.post(
        INITIATE,
        {"application_id": str(application.id), "method": method},
        format="json",
    )


class TestInitiate:
    def test_initiate_creates_pending_payment_with_checkout_ref(self, operator):
        application = submitted_application()
        resp = initiate(operator, application)
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["checkout_ref"].startswith("SBX-TEL-")
        assert body["status"] == "pending"
        from decimal import Decimal

        assert Decimal(str(body["amount"])) == Decimal(settings.ABIS_CLEARANCE_FEE_ETB)

    def test_initiate_on_draft_rejected(self, operator):
        application = ApplicationFactory()  # still draft
        assert initiate(operator, application).status_code == 400

    def test_repeat_initiate_returns_existing_pending(self, operator):
        application = submitted_application()
        first = initiate(operator, application).json()
        second = initiate(operator, application)
        assert second.status_code == 200  # not created again
        assert second.json()["payment_id"] == first["payment_id"]

    def test_cash_settles_immediately(self, operator):
        application = submitted_application()
        resp = initiate(operator, application, method="cash")
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "paid"
        assert body["receipt_no"].startswith("RCP-")
        application.refresh_from_db()
        assert application.status == ClearanceApplication.Status.PAID

    def test_initiate_after_paid_rejected(self, operator):
        application = submitted_application()
        initiate(operator, application, method="cash")
        assert initiate(operator, application).status_code == 400

    @pytest.mark.parametrize("role,expected", [("investigator", 403), ("auditor", 403)])
    def test_rbac(self, auth_client, role, expected):
        application = submitted_application()
        assert initiate(auth_client(role), application).status_code == expected

    def test_anonymous_401(self, api_client, db):
        resp = api_client.post(INITIATE, {}, format="json")
        assert resp.status_code == 401


class TestWebhook:
    def _pending_payment(self, operator) -> Payment:
        application = submitted_application()
        payment_id = initiate(operator, application).json()["payment_id"]
        return Payment.objects.get(id=payment_id)

    def test_valid_webhook_flips_application_to_paid(self, operator, api_client):
        payment = self._pending_payment(operator)
        resp = send_webhook(
            api_client,
            "telebirr",
            {"gateway_ref": payment.gateway_ref, "status": "paid", "amount": "300.00"},
        )
        assert resp.status_code == 200, resp.json()
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PAID
        assert payment.receipt_no.startswith("RCP-")
        assert payment.paid_at is not None
        payment.application.refresh_from_db()
        assert payment.application.status == ClearanceApplication.Status.PAID

    def test_bad_signature_403(self, operator, api_client):
        payment = self._pending_payment(operator)
        resp = send_webhook(
            api_client,
            "telebirr",
            {"gateway_ref": payment.gateway_ref, "status": "paid", "amount": "300.00"},
            signature="0" * 64,
        )
        assert resp.status_code == 403
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING

    def test_missing_signature_403(self, operator, api_client):
        payment = self._pending_payment(operator)
        resp = send_webhook(
            api_client,
            "telebirr",
            {"gateway_ref": payment.gateway_ref, "status": "paid"},
            signature="",
        )
        assert resp.status_code == 403

    def test_unknown_gateway_ref_404(self, api_client, db):
        resp = send_webhook(
            api_client, "telebirr", {"gateway_ref": "SBX-NOPE", "status": "paid"}
        )
        assert resp.status_code == 404

    def test_unknown_provider_404(self, api_client, db):
        resp = send_webhook(
            api_client,
            "paypal",
            {"gateway_ref": "x", "status": "paid"},
            signature="deadbeef",  # no secret exists for unknown providers
        )
        assert resp.status_code == 404

    def test_amount_mismatch_400(self, operator, api_client):
        payment = self._pending_payment(operator)
        resp = send_webhook(
            api_client,
            "telebirr",
            {"gateway_ref": payment.gateway_ref, "status": "paid", "amount": "1.00"},
        )
        assert resp.status_code == 400
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PENDING

    def test_failed_status_marks_payment_failed(self, operator, api_client):
        payment = self._pending_payment(operator)
        resp = send_webhook(
            api_client,
            "telebirr",
            {"gateway_ref": payment.gateway_ref, "status": "failed"},
        )
        assert resp.status_code == 200
        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED
        payment.application.refresh_from_db()
        assert payment.application.status == ClearanceApplication.Status.SUBMITTED

    def test_replay_is_idempotent(self, operator, api_client):
        payment = self._pending_payment(operator)
        payload = {
            "gateway_ref": payment.gateway_ref,
            "status": "paid",
            "amount": "300.00",
        }
        assert send_webhook(api_client, "telebirr", payload).status_code == 200
        payment.refresh_from_db()
        receipt = payment.receipt_no

        assert send_webhook(api_client, "telebirr", payload).status_code == 200
        payment.refresh_from_db()
        assert payment.receipt_no == receipt  # unchanged
        assert Payment.objects.filter(id=payment.id).count() == 1

    def test_wrong_provider_secret_rejected_cross_provider(self, operator, api_client):
        """A signature computed with chapa's secret must not pass telebirr."""
        payment = self._pending_payment(operator)
        payload = {"gateway_ref": payment.gateway_ref, "status": "paid"}
        body = json.dumps(payload).encode()
        resp = send_webhook(
            api_client, "telebirr", payload, signature=sign("chapa", body)
        )
        assert resp.status_code == 403


class TestListAndReconcile:
    def test_list_filter_by_status(self, operator):
        application = submitted_application()
        initiate(operator, application, method="cash")
        resp = operator.get("/api/v1/payments/", {"status": "paid"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_reconciliation_totals_and_persistence(self, operator):
        app_paid = submitted_application()
        initiate(operator, app_paid, method="cash")
        app_pending = submitted_application()
        initiate(operator, app_pending, method="telebirr")

        resp = operator.post("/api/v1/payments/reconcile/", {}, format="json")
        assert resp.status_code == 201
        totals = resp.json()["totals"]
        assert totals["count"] == 2
        assert totals["by_status"] == {"paid": 1, "pending": 1}
        assert totals["by_method"] == {"cash": 1, "telebirr": 1}
        assert totals["paid_total"] == settings.ABIS_CLEARANCE_FEE_ETB
        assert totals["mismatched_payments"] == []
        assert ReconciliationBatch.objects.count() == 1

    def test_reconciliations_listable(self, operator):
        operator.post("/api/v1/payments/reconcile/", {}, format="json")
        resp = operator.get("/api/v1/payments/reconciliations/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_auditor_cannot_reconcile(self, auth_client):
        resp = auth_client("auditor").post(
            "/api/v1/payments/reconcile/", {}, format="json"
        )
        assert resp.status_code == 403
