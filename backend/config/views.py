from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    summary="Service health check",
    description="Liveness probe. No auth, no database access.",
    responses=inline_serializer(
        name="HealthResponse",
        fields={
            "status": serializers.CharField(),
            "service": serializers.CharField(),
            "version": serializers.CharField(),
            "time": serializers.DateTimeField(),
        },
    ),
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    return Response(
        {
            "status": "ok",
            "service": "abis-backend",
            "version": "1.0.0",
            "time": timezone.now().isoformat(),
        }
    )
