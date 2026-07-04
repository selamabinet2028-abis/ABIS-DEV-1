from django.conf import settings
from rest_framework import serializers

from apps.basedata.models import Person

from .models import ClearanceApplication

DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


class ApplicationSerializer(serializers.ModelSerializer):
    person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(is_deleted=False)
    )
    person_no = serializers.CharField(source="person.person_no", read_only=True)
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )
    has_id_document = serializers.SerializerMethodField()

    class Meta:
        model = ClearanceApplication
        fields = [
            "id",
            "tracking_no",
            "person",
            "person_no",
            "person_name",
            "purpose",
            "status",
            "has_id_document",
            "submitted_at",
            "decision_note",
            "notes",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "tracking_no",
            "status",  # transitions only via dedicated endpoints (ADR-021)
            "has_id_document",
            "submitted_at",
            "decision_note",
            "created_by_username",
            "created_at",
        ]

    def get_has_id_document(self, obj: ClearanceApplication) -> bool:
        return bool(obj.id_document)


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        max_mb = settings.ABIS_MAX_UPLOAD_MB
        if value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"File exceeds the {max_mb} MB limit.")
        ext = (value.name.rsplit(".", 1)[-1] if "." in value.name else "").lower()
        if ext not in DOCUMENT_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}' — allowed: {sorted(DOCUMENT_EXTENSIONS)}."
            )
        return value
