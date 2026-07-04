from django.db.models import Count
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.audit.services import audit_instance
from apps.matching.models import MatchCandidate
from apps.matching.services import start_latent_search_job
from apps.preprocessing.services import sha256_hex

from .models import Case, EvidenceDocument, LatentPrint
from .permissions import InvestigationPermission
from .serializers import (CaseSerializer, EnhanceRequestSerializer,
                          EvidenceDocumentSerializer, EvidenceUploadSerializer,
                          LatentPrintSerializer, LatentSearchSerializer,
                          LatentUploadSerializer, MinutiaeUpdateSerializer)
from .services import enhance_latent, extract_minutiae, set_minutiae


class CaseViewSet(viewsets.ModelViewSet):
    queryset = (
        Case.objects.select_related("category", "lead_investigator")
        .prefetch_related("latents", "evidence")
        .all()
    )
    serializer_class = CaseSerializer
    permission_classes = [InvestigationPermission]
    search_fields = ["case_no", "title", "description"]
    filterset_fields = ["status", "category", "lead_investigator"]
    ordering_fields = ["created_at", "case_no"]
    http_method_names = ["get", "post", "patch", "head", "options"]  # no hard delete

    @extend_schema(
        summary="Upload a latent print into the case (multipart)",
        request=LatentUploadSerializer,
        responses={201: LatentPrintSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=LatentUploadSerializer,
    )
    def latents(self, request, pk=None):
        case = self.get_object()
        serializer = LatentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["image"]
        payload = upload.read()
        upload.seek(0)
        latent = LatentPrint.objects.create(
            case=case,
            modality=serializer.validated_data["modality"],
            image=upload,
            sha256=sha256_hex(payload),
            notes=serializer.validated_data.get("notes", ""),
            uploaded_by=request.user,
        )
        return Response(
            LatentPrintSerializer(latent).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Case evidence: list (GET) / upload with chain of custody (POST)",
        request=EvidenceUploadSerializer,
        responses={
            200: EvidenceDocumentSerializer(many=True),
            201: EvidenceDocumentSerializer,
        },
    )
    @action(
        detail=True,
        methods=["get", "post"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=EvidenceUploadSerializer,
    )
    def evidence(self, request, pk=None):
        case = self.get_object()
        if request.method == "GET":
            items = case.evidence.all()
            return Response(EvidenceDocumentSerializer(items, many=True).data)

        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        payload = upload.read()
        upload.seek(0)
        evidence = EvidenceDocument.objects.create(
            case=case,
            file=upload,
            description=serializer.validated_data.get("description", ""),
            collected_by=serializer.validated_data["collected_by"],
            collected_at=serializer.validated_data["collected_at"],
            sha256=sha256_hex(payload),
            uploaded_by=request.user,
        )
        return Response(
            EvidenceDocumentSerializer(evidence).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(summary="Case dashboard aggregates (counts, hits)")
    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        by_status = dict(
            Case.objects.values_list("status").annotate(count=Count("id")).order_by()
        )
        confirmed_hits = MatchCandidate.objects.filter(
            decision=MatchCandidate.Decision.HIT,
            job__probe_latent__isnull=False,
        ).count()
        return Response(
            {
                "cases_total": Case.objects.count(),
                "cases_by_status": by_status,
                "latents_total": LatentPrint.objects.count(),
                "latents_with_minutiae": LatentPrint.objects.exclude(
                    minutiae=[]
                ).count(),
                "evidence_total": EvidenceDocument.objects.count(),
                "confirmed_latent_hits": confirmed_hits,
            }
        )


class LatentPrintViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LatentPrint.objects.select_related("case", "uploaded_by").all()
    serializer_class = LatentPrintSerializer
    permission_classes = [InvestigationPermission]
    filterset_fields = ["case", "modality"]
    ordering_fields = ["created_at"]

    @extend_schema(
        summary="Apply enhancement operations (contrast/invert/rotate/crop), history kept",
        request=EnhanceRequestSerializer,
        responses={200: LatentPrintSerializer},
    )
    @action(detail=True, methods=["post"])
    def enhance(self, request, pk=None):
        latent = self.get_object()
        serializer = EnhanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            latent = enhance_latent(
                latent, serializer.validated_data["operations"], request.user
            )
        except ValueError as exc:
            return Response(
                {"operations": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(LatentPrintSerializer(latent).data)

    @extend_schema(
        summary="Auto-extract minutiae (deterministic stub; SDK replaces internals)",
        request=None,
        responses={200: LatentPrintSerializer},
    )
    @action(detail=True, methods=["post"], url_path="minutiae/extract")
    def minutiae_extract(self, request, pk=None):
        latent = self.get_object()
        try:
            extract_minutiae(latent, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        latent.refresh_from_db()
        return Response(LatentPrintSerializer(latent).data)

    @extend_schema(
        summary="Manually replace the minutiae set",
        request=MinutiaeUpdateSerializer,
        responses={200: LatentPrintSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="minutiae")
    def minutiae(self, request, pk=None):
        latent = self.get_object()
        serializer = MinutiaeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        latent = set_minutiae(
            latent, serializer.validated_data["minutiae"], request.user
        )
        return Response(LatentPrintSerializer(latent).data)

    @extend_schema(
        summary="Launch LT-TP / LT-LT search (202 + job id)",
        request=LatentSearchSerializer,
        responses={202: None},
    )
    @action(detail=True, methods=["post"])
    def search(self, request, pk=None):
        latent = self.get_object()
        serializer = LatentSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = start_latent_search_job(
            latent=latent,
            job_type=serializer.validated_data["job_type"],
            threshold=serializer.validated_data.get("threshold"),
            requested_by=request.user,
        )
        return Response({"job_id": job.id}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(summary="Download the original latent image (audited)")
    @action(detail=True, methods=["get"])
    def image(self, request, pk=None):
        latent = self.get_object()
        audit_instance(AuditLog.Action.VIEW, latent, changes={"accessed": "image"})
        return FileResponse(latent.image.open("rb"), filename=latent.image.name)

    @extend_schema(summary="Download the enhanced latent image (audited; 404 if none)")
    @action(detail=True, methods=["get"], url_path="enhanced-image")
    def enhanced_image(self, request, pk=None):
        latent = self.get_object()
        if not latent.enhanced_image:
            return Response(
                {"detail": "No enhanced image yet."}, status=status.HTTP_404_NOT_FOUND
            )
        audit_instance(
            AuditLog.Action.VIEW, latent, changes={"accessed": "enhanced_image"}
        )
        return FileResponse(
            latent.enhanced_image.open("rb"), filename=latent.enhanced_image.name
        )
