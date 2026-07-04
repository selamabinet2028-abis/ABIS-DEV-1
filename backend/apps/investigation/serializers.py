from django.conf import settings
from rest_framework import serializers

from .models import Case, EvidenceDocument, LatentPrint
from .services import ALLOWED_OPERATIONS

LATENT_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff"}
EVIDENCE_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "tif", "tiff"}

MINUTIA_TYPES = {"ridge_ending", "bifurcation"}


def _validate_upload(value, allowed: set[str], field: str):
    max_mb = settings.ABIS_MAX_UPLOAD_MB
    if value.size > max_mb * 1024 * 1024:
        raise serializers.ValidationError(f"{field} exceeds the {max_mb} MB limit.")
    ext = (value.name.rsplit(".", 1)[-1] if "." in value.name else "").lower()
    if ext not in allowed:
        raise serializers.ValidationError(
            f"Unsupported file type '.{ext}' — allowed: {sorted(allowed)}."
        )
    return value


class LatentPrintSerializer(serializers.ModelSerializer):
    case_no = serializers.CharField(source="case.case_no", read_only=True)
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )
    has_enhanced = serializers.SerializerMethodField()
    minutiae_count = serializers.SerializerMethodField()

    class Meta:
        model = LatentPrint
        fields = [
            "id",
            "case",
            "case_no",
            "modality",
            "sha256",
            "minutiae",
            "minutiae_count",
            "editor_history",
            "has_enhanced",
            "notes",
            "uploaded_by_username",
            "created_at",
        ]
        read_only_fields = fields

    def get_has_enhanced(self, obj: LatentPrint) -> bool:
        return bool(obj.enhanced_image)

    def get_minutiae_count(self, obj: LatentPrint) -> int:
        return len(obj.minutiae or [])


class LatentUploadSerializer(serializers.Serializer):
    modality = serializers.ChoiceField(choices=LatentPrint.Modality.choices)
    image = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_image(self, value):
        return _validate_upload(value, LATENT_EXTENSIONS, "image")


class EnhanceOperationSerializer(serializers.Serializer):
    op = serializers.ChoiceField(choices=sorted(ALLOWED_OPERATIONS))
    factor = serializers.FloatField(required=False, min_value=0.1, max_value=5.0)
    angle = serializers.FloatField(required=False, min_value=-360.0, max_value=360.0)
    box = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        required=False,
        min_length=4,
        max_length=4,
    )

    def validate(self, attrs):
        op = attrs["op"]
        if op == "contrast" and "factor" not in attrs:
            raise serializers.ValidationError({"factor": "Required for contrast."})
        if op == "rotate" and "angle" not in attrs:
            raise serializers.ValidationError({"angle": "Required for rotate."})
        if op == "crop":
            box = attrs.get("box")
            if not box:
                raise serializers.ValidationError({"box": "Required for crop."})
            left, top, right, bottom = box
            if left >= right or top >= bottom:
                raise serializers.ValidationError(
                    {"box": "Box must be [l, t, r, b] with l<r, t<b."}
                )
        return attrs


class EnhanceRequestSerializer(serializers.Serializer):
    operations = EnhanceOperationSerializer(many=True, allow_empty=False)


class MinutiaSerializer(serializers.Serializer):
    x = serializers.IntegerField(min_value=0)
    y = serializers.IntegerField(min_value=0)
    angle = serializers.FloatField(min_value=0.0, max_value=360.0)
    type = serializers.ChoiceField(choices=sorted(MINUTIA_TYPES))
    quality = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)


class MinutiaeUpdateSerializer(serializers.Serializer):
    minutiae = MinutiaSerializer(many=True)


LATENT_SEARCH_JOB_TYPES = ["LT-TP", "LT-LT"]


class LatentSearchSerializer(serializers.Serializer):
    job_type = serializers.ChoiceField(choices=LATENT_SEARCH_JOB_TYPES)
    threshold = serializers.FloatField(required=False, min_value=0.0, max_value=100.0)


class EvidenceDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username", read_only=True, default=None
    )

    class Meta:
        model = EvidenceDocument
        fields = [
            "id",
            "case",
            "file",
            "description",
            "collected_by",
            "collected_at",
            "sha256",
            "uploaded_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "case",
            "file",
            "sha256",
            "uploaded_by_username",
            "created_at",
        ]


class EvidenceUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    collected_by = serializers.CharField(max_length=150)
    collected_at = serializers.DateTimeField()

    def validate_file(self, value):
        return _validate_upload(value, EVIDENCE_EXTENSIONS, "file")


class CaseSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(
        source="category.code", read_only=True, default=None
    )
    lead_investigator_username = serializers.CharField(
        source="lead_investigator.username", read_only=True, default=None
    )
    latents = LatentPrintSerializer(many=True, read_only=True)
    evidence_count = serializers.IntegerField(source="evidence.count", read_only=True)

    class Meta:
        model = Case
        fields = [
            "id",
            "case_no",
            "title",
            "description",
            "category",
            "category_code",
            "status",
            "lead_investigator",
            "lead_investigator_username",
            "latents",
            "evidence_count",
            "created_at",
        ]
        read_only_fields = ["id", "case_no", "latents", "evidence_count", "created_at"]
