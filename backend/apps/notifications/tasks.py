from celery import shared_task
from django.utils import timezone


@shared_task(name="notifications.send_sms")
def send_sms(message_id: str) -> str:
    from .models import SmsMessage
    from .providers import get_sms_provider

    message = SmsMessage.objects.get(id=message_id)
    if message.status == SmsMessage.Status.SENT:
        return message.status  # idempotent replay
    try:
        message.provider_ref = get_sms_provider().send(message.to_number, message.body)
        message.status = SmsMessage.Status.SENT
        message.sent_at = timezone.now()
        message.save(update_fields=["provider_ref", "status", "sent_at"])
    except Exception as exc:  # provider failure → keep the row for retry/report
        message.status = SmsMessage.Status.FAILED
        message.error = str(exc)[:500]
        message.save(update_fields=["status", "error"])
    return message.status
