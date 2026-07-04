from rest_framework import serializers

from .models import Certificate


class ApplicationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class CertificateSerializer(serializers.ModelSerializer):
    person_no = serializers.CharField(source="person.person_no", read_only=True)
    holder_name = serializers.CharField(source="person.full_name", read_only=True)
    tracking_no = serializers.CharField(
        source="application.tracking_no", read_only=True
    )
    issued_by_username = serializers.CharField(
        source="issued_by.username", read_only=True, default=None
    )
    effective_status = serializers.CharField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id",
            "application",
            "person",
            "person_no",
            "holder_name",
            "tracking_no",
            "certificate_no",
            "verification_no",
            "status",
            "effective_status",
            "expires_at",
            "issued_by_username",
            "created_at",
        ]
        read_only_fields = fields
