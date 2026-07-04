from rest_framework import serializers

from .models import MatchCandidate, MatchJob


class MatchCandidateSerializer(serializers.ModelSerializer):
    person_no = serializers.CharField(
        source="person.person_no", read_only=True, default=None
    )
    person_name = serializers.CharField(
        source="person.full_name", read_only=True, default=None
    )
    record_modality = serializers.CharField(
        source="record.modality", read_only=True, default=None
    )
    record_position = serializers.CharField(
        source="record.position", read_only=True, default=None
    )
    latent_case_no = serializers.CharField(
        source="latent.case.case_no", read_only=True, default=None
    )
    verified_by_username = serializers.CharField(
        source="verified_by.username", read_only=True, default=None
    )

    class Meta:
        model = MatchCandidate
        fields = [
            "id",
            "job",
            "person",
            "person_no",
            "person_name",
            "record",
            "record_modality",
            "record_position",
            "latent",
            "latent_case_no",
            "score",
            "rank",
            "decision",
            "verified_by_username",
            "decided_at",
        ]
        read_only_fields = fields


class MatchJobSerializer(serializers.ModelSerializer):
    requested_by_username = serializers.CharField(
        source="requested_by.username", read_only=True, default=None
    )
    candidates = MatchCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = MatchJob
        fields = [
            "id",
            "job_type",
            "status",
            "probe_record",
            "probe_enrollment",
            "probe_latent",
            "threshold",
            "requested_by_username",
            "started_at",
            "finished_at",
            "error",
            "candidates",
            "created_at",
        ]
        read_only_fields = fields


class IdentifyRequestSerializer(serializers.Serializer):
    probe = serializers.UUIDField()  # BiometricRecord id (latent probes: T-009)
    job_type = serializers.ChoiceField(choices=MatchJob.JobType.choices)
    threshold = serializers.FloatField(required=False, min_value=0.0, max_value=100.0)


class IdentifyResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()


class VerifyRequestSerializer(serializers.Serializer):
    person_id = serializers.UUIDField()
    record_id = serializers.UUIDField()


class VerifyResponseSerializer(serializers.Serializer):
    match = serializers.BooleanField()
    score = serializers.FloatField()
    job_id = serializers.UUIDField()


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[MatchCandidate.Decision.HIT, MatchCandidate.Decision.NO_HIT]
    )
