from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.basedata.models import Person
from apps.enrollment.models import BiometricRecord

from .models import MatchCandidate, MatchJob
from .permissions import CandidateDecisionPermission, MatchingRunPermission
from .serializers import (DecisionSerializer, IdentifyRequestSerializer,
                          IdentifyResponseSerializer, MatchCandidateSerializer,
                          MatchJobSerializer, VerifyRequestSerializer,
                          VerifyResponseSerializer)
from .services import (JOB_PROBE_MODALITY, LATENT_JOB_TYPES, decide_candidate,
                       record_template, start_identify_job,
                       verify_person_record)


class IdentifyView(APIView):
    permission_classes = [MatchingRunPermission]

    @extend_schema(
        summary="Launch a 1:N identification job (202 + job id)",
        request=IdentifyRequestSerializer,
        responses={202: IdentifyResponseSerializer},
    )
    def post(self, request):
        serializer = IdentifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_type = serializer.validated_data["job_type"]

        if job_type in LATENT_JOB_TYPES:
            return Response(
                {
                    "job_type": [
                        "Latent-probe searches arrive with the investigation module (T-009)."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job_type == MatchJob.JobType.VERIFY:
            return Response(
                {"job_type": ["Use POST /match/verify/ for 1:1 verification."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if job_type == MatchJob.JobType.DEDUP:
            return Response(
                {"job_type": ["DEDUP jobs are launched by enrollment completion."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = get_object_or_404(
            BiometricRecord, id=serializer.validated_data["probe"]
        )
        expected_modality = JOB_PROBE_MODALITY[job_type]
        if record.modality != expected_modality:
            return Response(
                {"probe": [f"{job_type} requires a {expected_modality} record."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if record_template(record) is None:
            return Response(
                {"probe": ["Probe record has no template (was it accepted?)."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = start_identify_job(
            probe_record=record,
            job_type=job_type,
            threshold=serializer.validated_data.get("threshold"),
            requested_by=request.user,
        )
        return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)


class VerifyView(APIView):
    permission_classes = [MatchingRunPermission]

    @extend_schema(
        summary="Synchronous 1:1 verification of a record against a person",
        request=VerifyRequestSerializer,
        responses={200: VerifyResponseSerializer},
    )
    def post(self, request):
        serializer = VerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person = get_object_or_404(
            Person, id=serializer.validated_data["person_id"], is_deleted=False
        )
        record = get_object_or_404(
            BiometricRecord, id=serializer.validated_data["record_id"]
        )
        if record_template(record) is None:
            return Response(
                {"record_id": ["Record has no template (was it accepted?)."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job, matched, score = verify_person_record(
            person=person, record=record, requested_by=request.user
        )
        return Response({"match": matched, "score": score, "job_id": job.id})


class MatchJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        MatchJob.objects.select_related("requested_by")
        .prefetch_related(
            "candidates__person", "candidates__record", "candidates__verified_by"
        )
        .all()
    )
    serializer_class = MatchJobSerializer
    permission_classes = [MatchingRunPermission]
    filterset_fields = ["status", "job_type"]
    ordering_fields = ["created_at", "finished_at"]


class CandidateDecisionView(APIView):
    permission_classes = [CandidateDecisionPermission]

    @extend_schema(
        summary="Record the human decision on a match candidate",
        request=DecisionSerializer,
        responses={200: MatchCandidateSerializer},
    )
    def post(self, request, pk):
        candidate = get_object_or_404(MatchCandidate, id=pk)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = decide_candidate(
            candidate, decision=serializer.validated_data["decision"], user=request.user
        )
        return Response(MatchCandidateSerializer(candidate).data)
