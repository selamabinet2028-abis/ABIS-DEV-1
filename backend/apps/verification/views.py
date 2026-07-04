from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.apimgmt.services import authenticate_api_key
from apps.clearance.services import verify_qr_payload

from .models import VerificationEvent
from .services import public_payload, verify_by_number

PUBLIC_RESULT = inline_serializer(
    name="PublicVerifyResult",
    fields={
        "valid": drf_serializers.BooleanField(),
        "status": drf_serializers.CharField(),
        "holder_name_masked": drf_serializers.CharField(required=False),
        "issued_at": drf_serializers.DateTimeField(required=False),
        "expires_at": drf_serializers.DateTimeField(required=False),
    },
)


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class PublicVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    @extend_schema(
        summary="PUBLIC: verify a certificate by number (masked result)",
        responses={200: PUBLIC_RESULT},
        auth=[],
    )
    def get(self, request, verification_no):
        certificate, result = verify_by_number(
            verification_no,
            channel=VerificationEvent.Channel.PORTAL,
            verifier_ip=_client_ip(request),
        )
        return Response(public_payload(certificate, result))


class PublicQrVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public"

    @extend_schema(
        summary="PUBLIC: verify a scanned QR payload (signature + lookup)",
        request=inline_serializer(
            name="QrVerifyRequest", fields={"qr_payload": drf_serializers.CharField()}
        ),
        responses={200: PUBLIC_RESULT},
        auth=[],
    )
    def post(self, request):
        payload = request.data.get("qr_payload")
        if not isinstance(payload, str) or not payload:
            return Response(
                {"qr_payload": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            signature_ok, verification_no = verify_qr_payload(payload)
        except ValueError:
            return Response(
                {"qr_payload": ["Malformed QR payload."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not signature_ok:
            # Log the attempt with the claimed number, but never trust it.
            verify_by_number(
                verification_no or "",
                channel=VerificationEvent.Channel.QR,
                verifier_ip=_client_ip(request),
            )
            return Response({"valid": False, "status": "invalid"})

        certificate, result = verify_by_number(
            verification_no,
            channel=VerificationEvent.Channel.QR,
            verifier_ip=_client_ip(request),
        )
        return Response(public_payload(certificate, result))


class InstitutionalVerifyView(APIView):
    """Machine-to-machine verification: X-API-Key auth, full detail."""

    authentication_classes: list = []
    permission_classes = [AllowAny]  # the API key IS the auth
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "apikey"

    @extend_schema(
        summary="Institutional verify (X-API-Key) — full holder detail",
        request=inline_serializer(
            name="ApiVerifyRequest",
            fields={"verification_no": drf_serializers.CharField()},
        ),
        responses={200: PUBLIC_RESULT},
        auth=[],
    )
    def post(self, request):
        credential = authenticate_api_key(request.headers.get("X-API-Key"))
        if credential is None:
            return Response(
                {"detail": "Invalid or missing API key."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        verification_no = request.data.get("verification_no")
        if not verification_no:
            return Response(
                {"verification_no": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        certificate, result = verify_by_number(
            verification_no,
            channel=VerificationEvent.Channel.API,
            verifier_ip=_client_ip(request),
            api_credential=credential,
        )
        if certificate is None:
            return Response({"valid": False, "status": "invalid"})
        return Response(
            {
                "valid": result == "valid",
                "status": result,
                "holder_name": certificate.person.full_name,
                "person_no": certificate.person.person_no,
                "certificate_no": certificate.certificate_no,
                "tracking_no": certificate.application.tracking_no,
                "purpose": certificate.application.purpose,
                "issued_at": certificate.created_at,
                "expires_at": certificate.expires_at,
            }
        )
