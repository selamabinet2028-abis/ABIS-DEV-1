from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SendTestView, SmsOutboxViewSet, SmsTemplateViewSet

router = DefaultRouter()
router.register("sms/outbox", SmsOutboxViewSet, basename="sms-outbox")
router.register("sms/templates", SmsTemplateViewSet, basename="sms-template")

urlpatterns = [
    path("sms/send-test/", SendTestView.as_view(), name="sms-send-test"),
    *router.urls,
]
