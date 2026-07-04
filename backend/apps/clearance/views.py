from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import audit_instance
from apps.registration.models import ClearanceApplication
from apps.registration.serializers import ApplicationSerializer
from apps.registration.services import Status as AppStatus
from apps.registration.services import transition

from .models import Certificate
from .permissions import CertificatePermission, DecisionPermission
from .serializers import ApplicationDecisionSerializer, CertificateSerializer
from .services import decide, issue_certificate


class DecisionView(APIView):
    permission_classes = [DecisionPermission]

    @extend_schema(
        summary="Approve or reject an application in review (supervisor)",
        request=ApplicationDecisionSerializer,
        responses={200: ApplicationSerializer},
    )
    def post(self, request, pk):
        application = get_object_or_404(ClearanceApplication, id=pk)
        serializer = ApplicationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decide(
                application,
                decision=serializer.validated_data["decision"],
                note=serializer.validated_data.get("note", ""),
                by=request.user,
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(ApplicationSerializer(application).data)


class _TransitionView(APIView):
    """Thin staff endpoints advancing the ADR-021 status machine one step."""

    permission_classes = [CertificatePermission]
    target_status: str = ""
    summary = ""

    def post(self, request, pk):
        application = get_object_or_404(ClearanceApplication, id=pk)
        try:
            transition(application, self.target_status)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(ApplicationSerializer(application).data)


@extend_schema(
    summary="paid → biometrics_captured", request=None, responses=ApplicationSerializer
)
class BiometricsCapturedView(_TransitionView):
    target_status = AppStatus.BIOMETRICS_CAPTURED


@extend_schema(
    summary="biometrics_captured → in_review",
    request=None,
    responses=ApplicationSerializer,
)
class ToReviewView(_TransitionView):
    target_status = AppStatus.IN_REVIEW


class IssueCertificateView(APIView):
    permission_classes = [CertificatePermission]

    @extend_schema(
        summary="Issue the certificate (approved → certificate_issued; PDF + QR)",
        request=None,
        responses={201: CertificateSerializer},
    )
    def post(self, request, pk):
        application = get_object_or_404(ClearanceApplication, id=pk)
        try:
            certificate = issue_certificate(application, issued_by=request.user)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            CertificateSerializer(certificate).data, status=status.HTTP_201_CREATED
        )


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Certificate.objects.select_related(
        "person", "application", "issued_by"
    ).all()
    serializer_class = CertificateSerializer
    permission_classes = [CertificatePermission]
    filterset_fields = ["status", "person"]
    search_fields = ["certificate_no", "verification_no", "application__tracking_no"]

    @extend_schema(
        summary="Download the certificate PDF (access is audited)",
        responses={(200, "application/pdf"): bytes},
    )
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        certificate = self.get_object()
        audit_instance(AuditLog.Action.VIEW, certificate, changes={"accessed": "pdf"})
        return FileResponse(
            certificate.pdf_file.open("rb"),
            filename=f"{certificate.certificate_no}.pdf",
            content_type="application/pdf",
        )
