from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (BiometricsCapturedView, CertificateViewSet, DecisionView,
                    IssueCertificateView, ToReviewView)

router = DefaultRouter()
router.register("certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path(
        "applications/<uuid:pk>/decision/",
        DecisionView.as_view(),
        name="application-decision",
    ),
    path(
        "applications/<uuid:pk>/biometrics-captured/",
        BiometricsCapturedView.as_view(),
        name="application-biometrics-captured",
    ),
    path(
        "applications/<uuid:pk>/to-review/",
        ToReviewView.as_view(),
        name="application-to-review",
    ),
    path(
        "applications/<uuid:pk>/issue-certificate/",
        IssueCertificateView.as_view(),
        name="application-issue-certificate",
    ),
    *router.urls,
]
