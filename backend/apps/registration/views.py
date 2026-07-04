from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import ClearanceApplication
from .permissions import ApplicationPermission
from .serializers import ApplicationSerializer, DocumentUploadSerializer
from .services import submit


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = ClearanceApplication.objects.select_related("person", "created_by").all()
    serializer_class = ApplicationSerializer
    permission_classes = [ApplicationPermission]
    filterset_fields = ["status", "purpose", "person"]
    search_fields = [
        "tracking_no",
        "person__first_name",
        "person__middle_name",
        "person__last_name",
        "person__person_no",
    ]
    ordering_fields = ["created_at", "submitted_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]  # no hard delete

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Upload the scanned ID document (multipart)",
        request=DocumentUploadSerializer,
        responses={200: ApplicationSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=DocumentUploadSerializer,
    )
    def document(self, request, pk=None):
        application = self.get_object()
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application.id_document = serializer.validated_data["file"]
        application.save(update_fields=["id_document"])
        return Response(ApplicationSerializer(application).data)

    @extend_schema(
        summary="Submit the application (draft → submitted; requires ID document)",
        request=None,
        responses={200: ApplicationSerializer},
    )
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = self.get_object()
        try:
            submit(application)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(ApplicationSerializer(application).data)
