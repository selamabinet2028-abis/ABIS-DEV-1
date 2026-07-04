import datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Appointment, Station, TimeSlot
from .permissions import AppointmentStaffPermission, StationAdminPermission
from .serializers import (AppointmentSerializer, PublicBookingSerializer,
                          PublicSlotSerializer, PublicStationSerializer,
                          StationSerializer, TimeSlotSerializer)
from .services import availability, book_appointment


class PublicThrottleMixin:
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"


class PublicStationListView(PublicThrottleMixin, APIView):
    @extend_schema(
        summary="PUBLIC: active enrollment stations",
        responses={200: PublicStationSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        stations = Station.objects.filter(is_active=True)
        return Response(PublicStationSerializer(stations, many=True).data)


class PublicStationSlotsView(PublicThrottleMixin, APIView):
    @extend_schema(
        summary="PUBLIC: slot availability for a station and date",
        parameters=[
            OpenApiParameter("date", str, description="YYYY-MM-DD (default today)")
        ],
        responses={200: PublicSlotSerializer(many=True)},
        auth=[],
    )
    def get(self, request, pk):
        station = get_object_or_404(Station, id=pk, is_active=True)
        raw_date = request.query_params.get("date")
        if raw_date:
            try:
                date = datetime.date.fromisoformat(raw_date)
            except ValueError:
                return Response(
                    {"date": ["Use YYYY-MM-DD."]}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            date = timezone.localdate()
        if date < timezone.localdate():
            return Response(
                {"date": ["Date must be today or later."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(availability(station, date))


class PublicBookingView(PublicThrottleMixin, APIView):
    @extend_schema(
        summary="PUBLIC: book an appointment slot",
        request=PublicBookingSerializer,
        responses={201: AppointmentSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = PublicBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            appointment = book_appointment(
                station=data["station"],
                slot=data["slot"],
                date=data["date"],
                full_name=data["full_name"],
                phone=data["phone"],
                application=data["application"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = [StationAdminPermission]
    filterset_fields = ["is_active"]
    search_fields = ["code", "name", "address"]
    http_method_names = ["get", "post", "patch", "head", "options"]


class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.select_related("station").all()
    serializer_class = TimeSlotSerializer
    permission_classes = [StationAdminPermission]
    filterset_fields = ["station", "is_active"]
    http_method_names = ["get", "post", "patch", "head", "options"]


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related(
        "station", "slot", "application"
    ).all()
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentStaffPermission]
    filterset_fields = ["station", "date", "status"]
    search_fields = ["full_name", "phone"]
    ordering_fields = ["date", "created_at"]
    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]  # bookings come via public API
