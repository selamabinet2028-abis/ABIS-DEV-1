from rest_framework import serializers

from apps.registration.models import ClearanceApplication

from .models import Appointment, Station, TimeSlot


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "code", "name", "address", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PublicStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "code", "name", "address"]
        read_only_fields = fields


class TimeSlotSerializer(serializers.ModelSerializer):
    station_code = serializers.CharField(source="station.code", read_only=True)

    class Meta:
        model = TimeSlot
        fields = [
            "id",
            "station",
            "station_code",
            "start_time",
            "end_time",
            "capacity",
            "is_active",
        ]
        read_only_fields = ["id", "station_code"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "Must be after start_time."})
        return attrs


class PublicSlotSerializer(serializers.Serializer):
    slot_id = serializers.UUIDField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    capacity = serializers.IntegerField()
    available = serializers.IntegerField()


class PublicBookingSerializer(serializers.Serializer):
    station = serializers.PrimaryKeyRelatedField(
        queryset=Station.objects.filter(is_active=True)
    )
    slot = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.filter(is_active=True)
    )
    date = serializers.DateField()
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=32)
    tracking_no = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, attrs):
        tracking_no = attrs.pop("tracking_no", "")
        attrs["application"] = None
        if tracking_no:
            application = ClearanceApplication.objects.filter(
                tracking_no=tracking_no
            ).first()
            if application is None:
                raise serializers.ValidationError(
                    {"tracking_no": "Unknown tracking number."}
                )
            attrs["application"] = application
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    station_code = serializers.CharField(source="station.code", read_only=True)
    slot_window = serializers.SerializerMethodField()
    tracking_no = serializers.CharField(
        source="application.tracking_no", read_only=True, default=None
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "station",
            "station_code",
            "slot",
            "slot_window",
            "date",
            "status",
            "full_name",
            "phone",
            "tracking_no",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "station",
            "station_code",
            "slot",
            "slot_window",
            "date",
            "full_name",
            "phone",
            "tracking_no",
            "created_at",
        ]

    def get_slot_window(self, obj: Appointment) -> str:
        return f"{obj.slot.start_time:%H:%M}-{obj.slot.end_time:%H:%M}"
