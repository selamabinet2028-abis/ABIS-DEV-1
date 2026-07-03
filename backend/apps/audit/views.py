import django_filters
from rest_framework import viewsets

from apps.accounts.permissions import IsAdmin, IsAuditorReadOnly

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogFilter(django_filters.FilterSet):
    """API contract: ?entity=&entity_id=&actor=&action=&date_from=&date_to="""

    entity = django_filters.CharFilter(field_name="entity")
    entity_id = django_filters.CharFilter(field_name="entity_id")
    actor = django_filters.CharFilter(field_name="actor_username")
    action = django_filters.ChoiceFilter(choices=AuditLog.Action.choices)
    date_from = django_filters.IsoDateTimeFilter(field_name="at", lookup_expr="gte")
    date_to = django_filters.IsoDateTimeFilter(field_name="at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["entity", "entity_id", "actor", "action", "date_from", "date_to"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit trail for auditor/admin (insert-only elsewhere)."""

    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin | IsAuditorReadOnly]
    filterset_class = AuditLogFilter
    ordering_fields = ["at", "entity", "action"]
    search_fields = ["entity_repr", "actor_username", "entity_id"]
