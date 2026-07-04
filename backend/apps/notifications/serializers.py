from rest_framework import serializers

from .models import SmsMessage, SmsTemplate


class SmsTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsTemplate
        fields = ["id", "code", "body", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class SmsMessageSerializer(serializers.ModelSerializer):
    template_code = serializers.CharField(
        source="template.code", read_only=True, default=None
    )
    tracking_no = serializers.CharField(
        source="application.tracking_no", read_only=True, default=None
    )

    class Meta:
        model = SmsMessage
        fields = [
            "id",
            "to_number",
            "template_code",
            "body",
            "status",
            "provider_ref",
            "sent_at",
            "error",
            "tracking_no",
            "created_at",
        ]
        read_only_fields = fields


class SendTestSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=32)
    body = serializers.CharField(max_length=480)
