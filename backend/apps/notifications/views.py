from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SmsMessage, SmsTemplate
from .permissions import NotificationPermission
from .serializers import (SendTestSerializer, SmsMessageSerializer,
                          SmsTemplateSerializer)
from .services import enqueue_sms


class SmsOutboxViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SmsMessage.objects.select_related("template", "application").all()
    serializer_class = SmsMessageSerializer
    permission_classes = [NotificationPermission]
    filterset_fields = ["status", "template"]
    search_fields = ["to_number", "body", "application__tracking_no"]
    ordering_fields = ["created_at", "sent_at"]


class SmsTemplateViewSet(viewsets.ModelViewSet):
    queryset = SmsTemplate.objects.all()
    serializer_class = SmsTemplateSerializer
    permission_classes = [NotificationPermission]
    filterset_fields = ["is_active"]
    search_fields = ["code", "body"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


class SendTestView(APIView):
    permission_classes = [NotificationPermission]

    @extend_schema(
        summary="Send a test SMS (admin; dev provider logs to console)",
        request=SendTestSerializer,
        responses={201: SmsMessageSerializer},
    )
    def post(self, request):
        serializer = SendTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = enqueue_sms(
            to_number=serializer.validated_data["to"],
            body=serializer.validated_data["body"],
        )
        message.refresh_from_db()
        return Response(
            SmsMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
