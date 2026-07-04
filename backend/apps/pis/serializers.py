from django.conf import settings
from rest_framework import serializers

from .models import PhotoProbe

PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}


class PISSearchSerializer(serializers.Serializer):
    image = serializers.FileField()
    threshold = serializers.FloatField(required=False, min_value=0.0, max_value=100.0)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_image(self, value):
        max_mb = settings.ABIS_MAX_UPLOAD_MB
        if value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Image exceeds the {max_mb} MB limit.")
        ext = (value.name.rsplit(".", 1)[-1] if "." in value.name else "").lower()
        if ext not in PHOTO_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}' — allowed: {sorted(PHOTO_EXTENSIONS)}."
            )
        return value


class PhotoProbeSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )

    class Meta:
        model = PhotoProbe
        fields = ["id", "sha256", "notes", "uploaded_by_username", "created_at"]
        read_only_fields = fields


class PISSearchResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    probe_id = serializers.UUIDField()
