from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import audit_instance
from apps.matching.engines.base import get_engine
from apps.matching.models import MatchJob
from apps.matching.permissions import MatchingRunPermission
from apps.matching.serializers import (MatchCandidateSerializer,
                                       MatchJobSerializer)
from apps.matching.services import start_photo_search_job
from apps.preprocessing.services import sha256_hex

from .models import PhotoProbe
from .serializers import (PhotoProbeSerializer, PISSearchResponseSerializer,
                          PISSearchSerializer)


def _get_face_job(pk) -> MatchJob:
    return get_object_or_404(
        MatchJob.objects.prefetch_related(
            "candidates__person", "candidates__record", "candidates__verified_by"
        ),
        id=pk,
        job_type=MatchJob.JobType.FACE_1N,
    )


class PISSearchView(APIView):
    permission_classes = [MatchingRunPermission]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Face photo search: upload an image, launch FACE-1N (202)",
        request=PISSearchSerializer,
        responses={202: PISSearchResponseSerializer},
    )
    def post(self, request):
        serializer = PISSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["image"]
        payload = upload.read()
        upload.seek(0)

        try:
            get_engine().extract(payload)  # fail fast on undecodable uploads
        except ValueError:
            return Response(
                {"image": ["File is not a decodable image."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        probe = PhotoProbe.objects.create(
            image=upload,
            sha256=sha256_hex(payload),
            notes=serializer.validated_data.get("notes", ""),
            uploaded_by=request.user,
        )
        job = start_photo_search_job(
            photo_probe=probe,
            threshold=serializer.validated_data.get("threshold"),
            requested_by=request.user,
        )
        return Response(
            {"job_id": job.id, "probe_id": probe.id}, status=status.HTTP_202_ACCEPTED
        )


class PISJobView(APIView):
    permission_classes = [MatchingRunPermission]

    @extend_schema(
        summary="FACE-1N job status incl. probe info",
        responses={200: MatchJobSerializer},
    )
    def get(self, request, pk):
        job = _get_face_job(pk)
        body = MatchJobSerializer(job).data
        if job.probe_photo_id:
            body["probe_photo_detail"] = PhotoProbeSerializer(job.probe_photo).data
        return Response(body)


class PISJobCandidatesView(APIView):
    permission_classes = [MatchingRunPermission]

    @extend_schema(
        summary="Ranked candidates of a FACE-1N job (photo investigation review)",
        responses={200: MatchCandidateSerializer(many=True)},
    )
    def get(self, request, pk):
        job = _get_face_job(pk)
        return Response(
            {
                "job_id": job.id,
                "status": job.status,
                "candidates": MatchCandidateSerializer(
                    job.candidates.all(), many=True
                ).data,
            }
        )


class ProbeImageView(APIView):
    permission_classes = [MatchingRunPermission]

    @extend_schema(
        summary="Download the probe photo (access is audited)",
        responses={(200, "image/*"): bytes},
    )
    def get(self, request, pk):
        probe = get_object_or_404(PhotoProbe, id=pk)
        audit_instance(AuditLog.Action.VIEW, probe, changes={"accessed": "image"})
        return FileResponse(probe.image.open("rb"), filename=probe.image.name)
