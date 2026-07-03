from django.contrib.auth import authenticate
from django.utils import timezone
from drf_spectacular.utils import (OpenApiResponse, extend_schema,
                                   inline_serializer)
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Permission, Role, User, UserActivityLog
from .permissions import IsAdmin, IsAuditorReadOnly
from .serializers import (LoginRequestSerializer, PasswordChangeSerializer,
                          PermissionSerializer, RoleSerializer,
                          UserActivityLogSerializer, UserCreateSerializer,
                          UserSerializer, UserUpdateSerializer)
from .services import (blacklist_user_tokens, clear_refresh_cookie,
                       get_refresh_from_request, log_activity,
                       register_failed_login, register_successful_login,
                       set_refresh_cookie)

LOGIN_FAILED_DETAIL = "No active account found with the given credentials"
ACCOUNT_LOCKED_DETAIL = (
    "Account locked due to repeated failed sign-ins. Try again later."
)

_DETAIL_RESPONSE = inline_serializer(
    name="DetailResponse", fields={"detail": drf_serializers.CharField()}
)


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        summary="Login (sets httpOnly refresh cookie)",
        request=LoginRequestSerializer,
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={
                    "access": drf_serializers.CharField(),
                    "user": UserSerializer(),
                },
            ),
            401: _DETAIL_RESPONSE,
            403: _DETAIL_RESPONSE,
        },
        auth=[],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]

        user = (
            User.objects.filter(username=username)
            .select_related("role", "org_unit")
            .first()
        )
        if user and user.is_locked:
            log_activity(
                UserActivityLog.Action.LOGIN_BLOCKED, user=user, request=request
            )
            return Response(
                {"detail": ACCOUNT_LOCKED_DETAIL}, status=status.HTTP_403_FORBIDDEN
            )

        authenticated = authenticate(request, username=username, password=password)
        if authenticated is None:
            if user and user.is_active:
                register_failed_login(user, request)
            else:
                log_activity(
                    UserActivityLog.Action.LOGIN_FAILED,
                    username=username,
                    request=request,
                )
            return Response(
                {"detail": LOGIN_FAILED_DETAIL}, status=status.HTTP_401_UNAUTHORIZED
            )

        register_successful_login(authenticated, request)
        refresh = RefreshToken.for_user(authenticated)
        response = Response(
            {
                "access": str(refresh.access_token),
                "user": UserSerializer(authenticated).data,
            }
        )
        set_refresh_cookie(response, str(refresh))
        return response


class RefreshView(APIView):
    """Rotates the refresh token: cookie in, new cookie out, old one blacklisted."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh access token (reads httpOnly cookie; body fallback for API clients)",
        request=inline_serializer(
            name="RefreshRequest",
            fields={"refresh": drf_serializers.CharField(required=False)},
        ),
        responses={
            200: inline_serializer(
                name="RefreshResponse", fields={"access": drf_serializers.CharField()}
            ),
            401: _DETAIL_RESPONSE,
        },
        auth=[],
    )
    def post(self, request):
        raw = get_refresh_from_request(request)
        if not raw:
            return Response(
                {"detail": "No refresh token provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = TokenRefreshSerializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            # Explicit 401: with authentication_classes=[] DRF would map
            # InvalidToken (AuthenticationFailed) to 403, breaking the contract.
            return Response(
                {"detail": "Token is invalid or expired", "code": "token_not_valid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response({"access": serializer.validated_data["access"]})
        new_refresh = serializer.validated_data.get("refresh")
        if new_refresh:
            set_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Logout (blacklists refresh token, clears cookie)",
        request=None,
        responses={205: None},
        auth=[],
    )
    def post(self, request):
        raw = get_refresh_from_request(request)
        if raw:
            try:
                token = RefreshToken(raw)
                user = User.objects.filter(id=token.get("user_id")).first()
                token.blacklist()
                log_activity(UserActivityLog.Action.LOGOUT, user=user, request=request)
            except TokenError:
                pass  # already invalid — nothing to blacklist
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        clear_refresh_cookie(response)
        return response


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change own password (blacklists all refresh tokens)",
        request=PasswordChangeSerializer,
        responses={
            200: _DETAIL_RESPONSE,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user: User = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.password_changed_at = timezone.now()
        user.save(
            update_fields=["password", "must_change_password", "password_changed_at"]
        )

        blacklist_user_tokens(user)
        log_activity(UserActivityLog.Action.PASSWORD_CHANGE, user=user, request=request)

        response = Response({"detail": "Password changed. Sign in again."})
        clear_refresh_cookie(response)
        return response


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("role", "org_unit").order_by("username")
    permission_classes = [IsAdmin]
    filterset_fields = ["is_active", "role__name"]
    search_fields = ["username", "email", "first_name", "last_name", "badge_number"]
    ordering_fields = ["username", "date_joined", "last_login"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    @extend_schema(
        summary="Deactivate user (soft delete — accounts are never hard-deleted)",
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        blacklist_user_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Own profile", responses=UserSerializer)
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        summary="User activity log (admin, auditor read-only)",
        responses=UserActivityLogSerializer(many=True),
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAdmin | IsAuditorReadOnly],
    )
    def activity(self, request, pk=None):
        logs = UserActivityLog.objects.filter(user_id=pk)
        page = self.paginate_queryset(logs)
        serializer = UserActivityLogSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdmin]

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.users.exists():
            return Response(
                {"detail": "Role is assigned to users and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["module"]
    search_fields = ["codename", "name"]
