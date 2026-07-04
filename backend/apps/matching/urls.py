from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (CandidateDecisionView, IdentifyView, MatchJobViewSet,
                    VerifyView)

router = DefaultRouter()
router.register("match/jobs", MatchJobViewSet, basename="match-job")

urlpatterns = [
    path("match/identify/", IdentifyView.as_view(), name="match-identify"),
    path("match/verify/", VerifyView.as_view(), name="match-verify"),
    path(
        "match/candidates/<uuid:pk>/decision/",
        CandidateDecisionView.as_view(),
        name="match-candidate-decision",
    ),
    *router.urls,
]
