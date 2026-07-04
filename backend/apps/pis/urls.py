from django.urls import path

from .views import (PISJobCandidatesView, PISJobView, PISSearchView,
                    ProbeImageView)

urlpatterns = [
    path("pis/search/", PISSearchView.as_view(), name="pis-search"),
    path("pis/jobs/<uuid:pk>/", PISJobView.as_view(), name="pis-job"),
    path(
        "pis/jobs/<uuid:pk>/candidates/",
        PISJobCandidatesView.as_view(),
        name="pis-job-candidates",
    ),
    path(
        "pis/probes/<uuid:pk>/image/", ProbeImageView.as_view(), name="pis-probe-image"
    ),
]
