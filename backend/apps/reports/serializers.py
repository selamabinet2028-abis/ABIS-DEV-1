from rest_framework import serializers

from .models import ReportDefinition, ReportRun


class ReportDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "code",
            "name",
            "description",
            "default_params",
            "scheduled",
            "is_active",
        ]
        read_only_fields = fields


class ReportRunSerializer(serializers.ModelSerializer):
    definition_code = serializers.CharField(source="definition.code", read_only=True)
    requested_by_username = serializers.CharField(
        source="requested_by.username", read_only=True, default=None
    )

    class Meta:
        model = ReportRun
        fields = [
            "id",
            "definition",
            "definition_code",
            "format",
            "params",
            "status",
            "error",
            "requested_by_username",
            "started_at",
            "finished_at",
            "created_at",
        ]
        read_only_fields = fields


class RunRequestSerializer(serializers.Serializer):
    definition_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=ReportRun.Format.choices)
    params = serializers.DictField(required=False, default=dict)
