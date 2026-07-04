from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.registration.models import ClearanceApplication

from .models import Payment, ReconciliationBatch
from .permissions import PaymentPermission
from .serializers import (InitiateResponseSerializer, InitiateSerializer,
                          PaymentSerializer, ReconcileRequestSerializer,
                          ReconciliationBatchSerializer)
from .services import (WebhookPaymentNotFound, WebhookRejected,
                       WebhookSignatureError, initiate_payment,
                       process_webhook, run_reconciliation)


class InitiatePaymentView(APIView):
    permission_classes = [PaymentPermission]

    @extend_schema(
        summary="Initiate a clearance-fee payment (cash settles immediately)",
        request=InitiateSerializer,
        responses={201: InitiateResponseSerializer, 200: InitiateResponseSerializer},
    )
    def post(self, request):
        serializer = InitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = get_object_or_404(
            ClearanceApplication, id=serializer.validated_data["application_id"]
        )
        try:
            payment, created = initiate_payment(
                application=application,
                method=serializer.validated_data["method"],
                user=request.user,
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
                "payment_id": payment.id,
                "checkout_ref": payment.gateway_ref,
                "status": payment.status,
                "amount": payment.amount,
                "receipt_no": payment.receipt_no,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PaymentWebhookView(APIView):
    """Gateway callbacks — authenticated by HMAC signature, not JWT."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "webhook"

    @extend_schema(
        summary="Gateway webhook (X-ABIS-Signature: HMAC-SHA256 of raw body)",
        request=None,
        responses={200: PaymentSerializer},
        auth=[],
    )
    def post(self, request, provider):
        try:
            payment = process_webhook(
                provider_name=provider,
                raw_body=request.body,
                signature=request.headers.get("X-ABIS-Signature"),
            )
        except WebhookSignatureError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except WebhookPaymentNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except WebhookRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related("application", "initiated_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [PaymentPermission]
    filterset_fields = ["status", "method", "application"]
    search_fields = ["receipt_no", "gateway_ref", "application__tracking_no"]
    ordering_fields = ["created_at", "paid_at"]


class ReconcileView(APIView):
    permission_classes = [PaymentPermission]

    @extend_schema(
        summary="Run reconciliation over an optional date range",
        request=ReconcileRequestSerializer,
        responses={201: ReconciliationBatchSerializer},
    )
    def post(self, request):
        serializer = ReconcileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = run_reconciliation(
            date_from=serializer.validated_data.get("date_from"),
            date_to=serializer.validated_data.get("date_to"),
            user=request.user,
        )
        return Response(
            ReconciliationBatchSerializer(batch).data, status=status.HTTP_201_CREATED
        )


class ReconciliationBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationBatch.objects.select_related("run_by").all()
    serializer_class = ReconciliationBatchSerializer
    permission_classes = [PaymentPermission]
