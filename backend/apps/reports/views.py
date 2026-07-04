from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import audit_instance

from .models import ReportDefinition, ReportRun
from .permissions import KpiPermission, ReportPermission
from .serializers import (ReportDefinitionSerializer, ReportRunSerializer,
                          RunRequestSerializer)
from .services import dashboard_kpis, start_report_run

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}


class ReportDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportDefinition.objects.filter(is_active=True)
    serializer_class = ReportDefinitionSerializer
    permission_classes = [ReportPermission]
    search_fields = ["code", "name"]


class RunReportView(APIView):
    permission_classes = [ReportPermission]

    @extend_schema(
        summary="Run a report (202 + run id; poll the run, then download)",
        request=RunRequestSerializer,
        responses={202: ReportRunSerializer},
    )
    def post(self, request):
        serializer = RunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        definition = get_object_or_404(
            ReportDefinition,
            id=serializer.validated_data["definition_id"],
            is_active=True,
        )
        run = start_report_run(
            definition=definition,
            params=serializer.validated_data.get("params") or {},
            format=serializer.validated_data["format"],
            requested_by=request.user,
        )
        run.refresh_from_db()
        return Response(ReportRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)


class ReportRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportRun.objects.select_related("definition", "requested_by").all()
    serializer_class = ReportRunSerializer
    permission_classes = [ReportPermission]
    filterset_fields = ["status", "definition", "format"]

    @extend_schema(
        summary="Download the rendered report (access is audited)",
        responses={(200, "application/octet-stream"): bytes},
    )
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        run = self.get_object()
        if run.status != ReportRun.Status.DONE or not run.file:
            return Response(
                {"detail": f"Report is not ready (status: {run.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit_instance(AuditLog.Action.EXPORT, run, changes={"accessed": "file"})
        return FileResponse(
            run.file.open("rb"),
            filename=f"{run.definition.code}.{run.format}",
            content_type=CONTENT_TYPES.get(run.format, "application/octet-stream"),
        )


class DashboardKpiView(APIView):
    permission_classes = [KpiPermission]

    @extend_schema(summary="Role-scoped dashboard KPIs", responses={200: dict})
    def get(self, request):
        role = request.user.role_name or (
            "admin" if request.user.is_superuser else None
        )
        return Response(dashboard_kpis(role))
