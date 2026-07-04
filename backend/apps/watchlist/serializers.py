from rest_framework import serializers

from apps.basedata.models import Person

from .models import Watchlist, WatchlistAlert, WatchlistEntry


class WatchlistSerializer(serializers.ModelSerializer):
    entry_count = serializers.IntegerField(source="entries.count", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = Watchlist
        fields = [
            "id",
            "name",
            "list_type",
            "description",
            "is_active",
            "entry_count",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = ["id", "entry_count", "created_by_username", "created_at"]


class WatchlistEntrySerializer(serializers.ModelSerializer):
    person_no = serializers.CharField(source="person.person_no", read_only=True)
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    added_by_username = serializers.CharField(
        source="added_by.username", read_only=True, default=None
    )

    class Meta:
        model = WatchlistEntry
        fields = [
            "id",
            "watchlist",
            "person",
            "person_no",
            "person_name",
            "reason",
            "severity",
            "active",
            "added_by_username",
            "created_at",
        ]
        read_only_fields = ["id", "watchlist", "added_by_username", "created_at"]


class WatchlistEntryCreateSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(is_deleted=False)
    )
    reason = serializers.CharField(max_length=500)
    severity = serializers.ChoiceField(
        choices=WatchlistEntry.Severity.choices, default=WatchlistEntry.Severity.MEDIUM
    )


class WatchlistEntryUpdateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False)
    severity = serializers.ChoiceField(
        choices=WatchlistEntry.Severity.choices, required=False
    )
    active = serializers.BooleanField(required=False)


class WatchlistAlertSerializer(serializers.ModelSerializer):
    person = serializers.UUIDField(source="entry.person_id", read_only=True)
    person_no = serializers.CharField(source="entry.person.person_no", read_only=True)
    person_name = serializers.CharField(source="entry.person.full_name", read_only=True)
    watchlist_name = serializers.CharField(
        source="entry.watchlist.name", read_only=True
    )
    list_type = serializers.CharField(
        source="entry.watchlist.list_type", read_only=True
    )
    severity = serializers.CharField(source="entry.severity", read_only=True)
    job_type = serializers.CharField(source="trigger_job.job_type", read_only=True)
    acknowledged_by_username = serializers.CharField(
        source="acknowledged_by.username", read_only=True, default=None
    )

    class Meta:
        model = WatchlistAlert
        fields = [
            "id",
            "entry",
            "person",
            "person_no",
            "person_name",
            "watchlist_name",
            "list_type",
            "severity",
            "trigger_job",
            "job_type",
            "score",
            "message",
            "acknowledged",
            "acknowledged_by_username",
            "acknowledged_at",
            "created_at",
        ]
        read_only_fields = fields
