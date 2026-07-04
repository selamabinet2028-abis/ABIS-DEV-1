from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Watchlist, WatchlistAlert, WatchlistEntry
from .permissions import WatchlistPermission
from .serializers import (WatchlistAlertSerializer,
                          WatchlistEntryCreateSerializer,
                          WatchlistEntrySerializer,
                          WatchlistEntryUpdateSerializer, WatchlistSerializer)
from .services import acknowledge_alert


class WatchlistViewSet(viewsets.ModelViewSet):
    queryset = Watchlist.objects.prefetch_related("entries").all()
    serializer_class = WatchlistSerializer
    permission_classes = [WatchlistPermission]
    filterset_fields = ["list_type", "is_active"]
    search_fields = ["name", "description"]
    # DELETE stays allowed at dispatch level for the nested entry action;
    # destroying a whole watchlist is blocked below (deactivate instead).
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "detail": "Watchlists are deactivated (PATCH is_active=false), never deleted."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @extend_schema(
        summary="Watchlist entries: list (GET) / add person (POST)",
        request=WatchlistEntryCreateSerializer,
        responses={
            200: WatchlistEntrySerializer(many=True),
            201: WatchlistEntrySerializer,
        },
    )
    @action(
        detail=True,
        methods=["get", "post"],
        serializer_class=WatchlistEntryCreateSerializer,
    )
    def entries(self, request, pk=None):
        watchlist = self.get_object()
        if request.method == "GET":
            entries = watchlist.entries.select_related("person", "added_by")
            return Response(WatchlistEntrySerializer(entries, many=True).data)

        serializer = WatchlistEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if watchlist.entries.filter(
            person=serializer.validated_data["person"]
        ).exists():
            return Response(
                {"person": ["Person is already on this watchlist."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry = WatchlistEntry.objects.create(
            watchlist=watchlist,
            person=serializer.validated_data["person"],
            reason=serializer.validated_data["reason"],
            severity=serializer.validated_data["severity"],
            added_by=request.user,
        )
        return Response(
            WatchlistEntrySerializer(entry).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Update (PATCH) or deactivate (DELETE) one entry",
        request=WatchlistEntryUpdateSerializer,
        responses={200: WatchlistEntrySerializer, 204: None},
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"entries/(?P<entry_id>[0-9a-f-]+)",
        serializer_class=WatchlistEntryUpdateSerializer,
    )
    def entry_detail(self, request, pk=None, entry_id=None):
        entry = get_object_or_404(WatchlistEntry, id=entry_id, watchlist_id=pk)
        if request.method == "DELETE":
            entry.active = False
            entry.save(update_fields=["active"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = WatchlistEntryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(entry, field, value)
        entry.save(update_fields=list(serializer.validated_data))
        return Response(WatchlistEntrySerializer(entry).data)


class WatchlistAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WatchlistAlert.objects.select_related(
        "entry__person", "entry__watchlist", "trigger_job", "acknowledged_by"
    ).all()
    serializer_class = WatchlistAlertSerializer
    permission_classes = [WatchlistPermission]
    filterset_fields = ["acknowledged", "entry__watchlist", "entry__severity"]
    ordering_fields = ["created_at"]

    @extend_schema(
        summary="Acknowledge an alert (idempotent)",
        request=None,
        responses={200: WatchlistAlertSerializer},
    )
    @action(detail=True, methods=["post"])
    def ack(self, request, pk=None):
        alert = acknowledge_alert(self.get_object(), request.user)
        return Response(WatchlistAlertSerializer(alert).data)
