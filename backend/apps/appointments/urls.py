from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (AppointmentViewSet, PublicBookingView,
                    PublicStationListView, PublicStationSlotsView,
                    StationViewSet, TimeSlotViewSet)

router = DefaultRouter()
router.register("stations", StationViewSet, basename="station")
router.register("time-slots", TimeSlotViewSet, basename="time-slot")
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("public/stations/", PublicStationListView.as_view(), name="public-stations"),
    path(
        "public/stations/<uuid:pk>/slots/",
        PublicStationSlotsView.as_view(),
        name="public-station-slots",
    ),
    path("public/appointments/", PublicBookingView.as_view(), name="public-booking"),
    *router.urls,
]
