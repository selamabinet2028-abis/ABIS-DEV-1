from django.conf import settings
from rest_framework import serializers

from .models import InvestigationCategory, LookupValue, OrgUnit, Person

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}


class OrgUnitSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, default=None
    )
    children_count = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "parent", "parent_name", "children_count", "created_at"]

    def validate_parent(self, value: OrgUnit | None) -> OrgUnit | None:
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("An org unit cannot be its own parent.")
        return value


class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "person_no",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "gender",
            "date_of_birth",
            "nationality",
            "national_id_no",
            "addresses",
            "photo",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "person_no", "photo", "created_at", "updated_at"]

    def validate_national_id_no(self, value: str | None) -> str | None:
        return value.strip() or None if value else None  # '' would break unique NULLs

    def validate_addresses(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "addresses must be a list of address objects."
            )
        if any(not isinstance(item, dict) for item in value):
            raise serializers.ValidationError("each address must be an object.")
        return value


class PersonPhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, value):
        max_mb = settings.ABIS_MAX_UPLOAD_MB
        if value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Photo exceeds the {max_mb} MB limit.")
        ext = (value.name.rsplit(".", 1)[-1] if "." in value.name else "").lower()
        if ext not in ALLOWED_PHOTO_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}' — allowed: jpg, jpeg, png."
            )
        return value


class LookupValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = LookupValue
        fields = ["id", "category", "code", "label", "sort_order", "is_active"]


class InvestigationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationCategory
        fields = ["id", "code", "name", "description", "is_active"]
