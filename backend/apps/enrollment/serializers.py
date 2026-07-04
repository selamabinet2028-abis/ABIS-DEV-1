from django.conf import settings
from rest_framework import serializers

from apps.appointments.models import Station
from apps.basedata.models import Person

from .models import MODALITY_POSITIONS, BiometricRecord, Enrollment, Modality

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff"}


class BiometricRecordSerializer(serializers.ModelSerializer):
    has_template = serializers.SerializerMethodField()

    class Meta:
        model = BiometricRecord
        fields = [
            "id",
            "enrollment",
            "person",
            "modality",
            "position",
            "sha256",
            "quality_score",
            "accepted",
            "nist_meta",
            "has_template",
            "created_at",
        ]
        read_only_fields = fields

    def get_has_template(self, obj: BiometricRecord) -> bool:
        return hasattr(obj, "template")


class EnrollmentSerializer(serializers.ModelSerializer):
    person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(is_deleted=False)
    )
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_no = serializers.CharField(source="person.person_no", read_only=True)
    station = serializers.PrimaryKeyRelatedField(
        queryset=Station.objects.filter(is_active=True), required=False, allow_null=True
    )
    station_code = serializers.CharField(
        source="station.code", read_only=True, default=None
    )
    operator_username = serializers.CharField(
        source="operator.username", read_only=True, default=None
    )
    records = BiometricRecordSerializer(many=True, read_only=True)
    quality_summary = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "person",
            "person_no",
            "person_name",
            "station",
            "station_code",
            "operator_username",
            "status",
            "completed_at",
            "notes",
            "quality_summary",
            "records",
            "created_at",
        ]
        read_only_fields = ["id", "status", "completed_at", "records", "created_at"]

    def get_quality_summary(self, obj: Enrollment) -> dict:
        summary: dict[str, dict[str, int | float]] = {}
        for record in obj.records.all():
            entry = summary.setdefault(
                record.modality, {"count": 0, "accepted": 0, "avg_quality": 0.0}
            )
            entry["count"] += 1
            entry["accepted"] += int(record.accepted)
            entry["avg_quality"] += record.quality_score
        for entry in summary.values():
            entry["avg_quality"] = round(entry["avg_quality"] / entry["count"], 2)
        return summary


class BiometricCaptureSerializer(serializers.Serializer):
    modality = serializers.ChoiceField(choices=Modality.choices)
    position = serializers.CharField()
    image = serializers.FileField()

    def validate_image(self, value):
        max_mb = settings.ABIS_MAX_UPLOAD_MB
        if value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Image exceeds the {max_mb} MB limit.")
        ext = (value.name.rsplit(".", 1)[-1] if "." in value.name else "").lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}' — allowed: {sorted(ALLOWED_IMAGE_EXTENSIONS)}."
            )
        return value

    def validate(self, attrs):
        valid_positions = MODALITY_POSITIONS[attrs["modality"]]
        if attrs["position"] not in valid_positions:
            raise serializers.ValidationError(
                {
                    "position": (
                        f"Invalid position '{attrs['position']}' for modality "
                        f"'{attrs['modality']}' — allowed: {sorted(valid_positions)}."
                    )
                }
            )
        return attrs


class CaptureResultSerializer(serializers.Serializer):
    record_id = serializers.UUIDField()
    quality_score = serializers.IntegerField(min_value=1, max_value=5)
    accepted = serializers.BooleanField()


class CompleteResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    dedup_job_id = serializers.UUIDField(allow_null=True)
