from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (DashboardKpiView, ReportDefinitionViewSet,
                    ReportRunViewSet, RunReportView)

router = DefaultRouter()
router.register(
    "reports/definitions", ReportDefinitionViewSet, basename="report-definition"
)
router.register("reports/runs", ReportRunViewSet, basename="report-run")

urlpatterns = [
    path("reports/run/", RunReportView.as_view(), name="report-run-start"),
    path("dashboard/kpis/", DashboardKpiView.as_view(), name="dashboard-kpis"),
    *router.urls,
]
