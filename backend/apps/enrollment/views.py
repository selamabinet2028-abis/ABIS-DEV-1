from django.core.exceptions import ValidationError
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.audit.services import audit_instance

from .models import BiometricRecord, Enrollment
from .permissions import EnrollmentPermission
from .serializers import (BiometricCaptureSerializer,
                          BiometricRecordSerializer, CaptureResultSerializer,
                          CompleteResultSerializer, EnrollmentSerializer)
from .services import capture_biometric, complete_enrollment


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = (
        Enrollment.objects.select_related("person", "station", "operator")
        .prefetch_related("records__template")
        .all()
    )
    serializer_class = EnrollmentSerializer
    permission_classes = [EnrollmentPermission]
    filterset_fields = ["status", "person", "station"]
    ordering_fields = ["created_at", "completed_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]  # no hard delete

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    @extend_schema(
        summary="Capture one biometric image (multipart: modality, position, image)",
        request=BiometricCaptureSerializer,
        responses={201: CaptureResultSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=BiometricCaptureSerializer,
    )
    def biometrics(self, request, pk=None):
        enrollment = self.get_object()
        if enrollment.status != Enrollment.Status.IN_PROGRESS:
            return Response(
                {"detail": "Enrollment is not in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = BiometricCaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = capture_biometric(
                enrollment=enrollment,
                modality=serializer.validated_data["modality"],
                position=serializer.validated_data["position"],
                uploaded_file=serializer.validated_data["image"],
                user=request.user,
            )
        except ValueError:
            return Response(
                {"image": ["File is not a decodable image."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "record_id": record.id,
                "quality_score": record.quality_score,
                "accepted": record.accepted,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Complete the capture session (dedup job wired in T-008)",
        request=None,
        responses={200: CompleteResultSerializer},
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        enrollment = self.get_object()
        try:
            result = complete_enrollment(enrollment)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(result)


class BiometricRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BiometricRecord.objects.select_related("person", "enrollment").all()
    serializer_class = BiometricRecordSerializer
    permission_classes = [EnrollmentPermission]
    filterset_fields = ["person", "enrollment", "modality", "accepted"]

    @extend_schema(
        summary="Download the biometric image (access is audited)",
        responses={(200, "image/*"): bytes},
    )
    @action(detail=True, methods=["get"])
    def image(self, request, pk=None):
        record = self.get_object()
        audit_instance(AuditLog.Action.VIEW, record, changes={"accessed": "image"})
        return FileResponse(record.image.open("rb"), filename=record.image.name)
