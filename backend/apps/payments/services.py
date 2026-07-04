"""Payment services: initiation, webhook processing, receipts, reconciliation."""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Count, Sum
from django.utils import timezone

from apps.registration.models import ClearanceApplication
from apps.registration.services import mark_paid

from .models import Payment, ReconciliationBatch
from .providers.base import get_provider

logger = logging.getLogger(__name__)

GATEWAY_METHODS = {
    Payment.Method.TELEBIRR,
    Payment.Method.CBE_BIRR,
    Payment.Method.CHAPA,
}

# Application states at/after "paid" — webhook replays against these are benign.
PAID_OR_LATER = {
    ClearanceApplication.Status.PAID,
    ClearanceApplication.Status.BIOMETRICS_CAPTURED,
    ClearanceApplication.Status.IN_REVIEW,
    ClearanceApplication.Status.APPROVED,
    ClearanceApplication.Status.CERTIFICATE_ISSUED,
}


class WebhookSignatureError(Exception):
    pass


class WebhookPaymentNotFound(Exception):
    pass


class WebhookRejected(Exception):
    pass


def clearance_fee() -> Decimal:
    return Decimal(settings.ABIS_CLEARANCE_FEE_ETB)


def generate_receipt_no() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('abis_receipt_no_seq')")
        (value,) = cursor.fetchone()
    return f"RCP-{timezone.now().year}-{value:06d}"


def _settle(payment: Payment) -> Payment:
    payment.status = Payment.Status.PAID
    payment.paid_at = timezone.now()
    payment.receipt_no = generate_receipt_no()
    payment.save(update_fields=["status", "paid_at", "receipt_no"])

    application = payment.application
    if application.status == ClearanceApplication.Status.SUBMITTED:
        mark_paid(application)
    elif application.status not in PAID_OR_LATER:
        logger.warning(
            "Payment %s settled but application %s is in state %s",
            payment.id,
            application.tracking_no,
            application.status,
        )
    return payment


def initiate_payment(
    *, application: ClearanceApplication, method: str, user
) -> tuple[Payment, bool]:
    """Create (or return the pending) payment. Returns (payment, created)."""
    if application.status != ClearanceApplication.Status.SUBMITTED:
        raise ValidationError(
            "Payments can only be initiated for submitted applications."
        )
    if application.payments.filter(status=Payment.Status.PAID).exists():
        raise ValidationError("Application is already paid.")

    existing = application.payments.filter(
        status=Payment.Status.PENDING, method=method
    ).first()
    if existing:
        return existing, False

    payment = Payment.objects.create(
        application=application,
        amount=clearance_fee(),
        method=method,
        initiated_by=user,
    )

    if method == Payment.Method.CASH:
        _settle(payment)  # front desk collected cash — settle immediately
        return payment, True

    checkout = get_provider(method).create_checkout(payment)
    payment.gateway_ref = checkout["gateway_ref"]
    payment.save(update_fields=["gateway_ref"])
    return payment, True


def process_webhook(
    *, provider_name: str, raw_body: bytes, signature: str | None
) -> Payment:
    """Validate + apply one gateway webhook. Raises Webhook* on rejection."""
    if provider_name not in GATEWAY_METHODS:
        raise WebhookPaymentNotFound(f"Unknown provider '{provider_name}'.")

    provider = get_provider(provider_name)
    if not provider.verify_signature(raw_body, signature):
        raise WebhookSignatureError("Invalid or missing webhook signature.")

    try:
        data = json.loads(raw_body.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise WebhookRejected("Webhook body is not valid JSON.") from exc

    event = provider.parse_webhook(data)
    payment = Payment.objects.filter(
        method=provider_name, gateway_ref=event["gateway_ref"]
    ).first()
    if payment is None:
        raise WebhookPaymentNotFound("No payment matches this gateway reference.")

    if payment.status == Payment.Status.PAID:
        return payment  # idempotent replay

    if (
        event.get("amount") is not None
        and Decimal(str(event["amount"])) != payment.amount
    ):
        raise WebhookRejected("Webhook amount does not match the payment amount.")

    payment.raw_webhook = data
    if event["status"] == "paid":
        payment.save(update_fields=["raw_webhook"])
        _settle(payment)
    elif event["status"] == "failed":
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "raw_webhook"])
    else:
        raise WebhookRejected(f"Unsupported webhook status '{event['status']}'.")
    return payment


def run_reconciliation(
    *, date_from=None, date_to=None, user=None
) -> ReconciliationBatch:
    payments = Payment.objects.all()
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)

    by_method = {
        row["method"]: row["count"]
        for row in payments.values("method").annotate(count=Count("id")).order_by()
    }
    by_status = {
        row["status"]: row["count"]
        for row in payments.values("status").annotate(count=Count("id")).order_by()
    }
    paid = payments.filter(status=Payment.Status.PAID)
    paid_total = paid.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    mismatches = [
        str(payment.id)
        for payment in paid.select_related("application")
        if payment.application.status not in PAID_OR_LATER
    ]

    return ReconciliationBatch.objects.create(
        date_from=date_from,
        date_to=date_to,
        run_by=user,
        totals={
            "count": payments.count(),
            "by_method": by_method,
            "by_status": by_status,
            "paid_total": str(paid_total),
            "mismatched_payments": mismatches,
        },
    )
