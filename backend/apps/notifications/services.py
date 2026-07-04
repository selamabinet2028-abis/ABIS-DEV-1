"""Notification services: template rendering + outbox enqueue + triggers."""

from __future__ import annotations

import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction

from apps.registration.models import ClearanceApplication

from .models import SmsMessage, SmsTemplate

logger = logging.getLogger(__name__)

TEMPLATE_BY_STATUS = {
    ClearanceApplication.Status.SUBMITTED: "application_submitted",
    ClearanceApplication.Status.PAID: "payment_received",
    ClearanceApplication.Status.CERTIFICATE_ISSUED: "certificate_ready",
}


def safe_format(template_body: str, context: dict) -> str:
    return template_body.format_map(defaultdict(str, context))


def _dispatch(message: SmsMessage) -> None:
    from .tasks import send_sms

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        send_sms.delay(str(message.id))
    else:
        transaction.on_commit(lambda: send_sms.delay(str(message.id)))


def enqueue_sms(
    *, to_number: str, body: str, template: SmsTemplate | None = None, application=None
) -> SmsMessage:
    message = SmsMessage.objects.create(
        to_number=to_number, body=body, template=template, application=application
    )
    _dispatch(message)
    return message


def build_application_context(application: ClearanceApplication) -> dict:
    context = {
        "name": application.person.full_name,
        "tracking_no": application.tracking_no,
        "status": application.status,
    }
    paid_payment = application.payments.filter(status="paid").first()
    if paid_payment:
        context["receipt_no"] = paid_payment.receipt_no or ""
    certificate = getattr(application, "certificate", None)
    if certificate:
        context["verification_no"] = certificate.verification_no
        context["certificate_no"] = certificate.certificate_no
    return context


def notify_application_status(application: ClearanceApplication, new_status: str):
    """Trigger for submitted/paid/certificate_issued transitions."""
    code = TEMPLATE_BY_STATUS.get(new_status)
    if code is None:
        return None
    if not application.contact_phone:
        logger.info(
            "No contact phone on %s — skipping '%s' SMS", application.tracking_no, code
        )
        return None
    template = SmsTemplate.objects.filter(code=code, is_active=True).first()
    if template is None:
        logger.warning("SMS template '%s' missing or inactive — skipping", code)
        return None

    body = safe_format(template.body, build_application_context(application))
    return enqueue_sms(
        to_number=application.contact_phone,
        body=body,
        template=template,
        application=application,
    )
