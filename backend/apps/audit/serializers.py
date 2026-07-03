from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_username",
            "action",
            "entity",
            "entity_id",
            "entity_repr",
            "changes",
            "ip",
            "user_agent",
            "at",
        ]
        read_only_fields = fields
