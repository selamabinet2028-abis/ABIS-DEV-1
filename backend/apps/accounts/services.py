"""Account services: activity logging, lockout policy, refresh-token cookie."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (BlacklistedToken,
                                                             OutstandingToken)

from .models import User, UserActivityLog


def client_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_activity(
    action: str,
    *,
    user: User | None = None,
    username: str = "",
    request: HttpRequest | None = None,
    detail: str = "",
) -> UserActivityLog:
    return UserActivityLog.objects.create(
        user=user,
        username=username or (user.username if user else ""),
        action=action,
        ip_address=client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:512] if request else ""),
        detail=detail,
    )


def register_failed_login(user: User, request: HttpRequest | None) -> None:
    """Count a failure; lock the account when the threshold is reached."""
    cfg = settings.ABIS_AUTH
    user.failed_login_attempts += 1
    log_activity(UserActivityLog.Action.LOGIN_FAILED, user=user, request=request)

    if user.failed_login_attempts >= cfg["LOCKOUT_THRESHOLD"]:
        user.locked_until = timezone.now() + timedelta(minutes=cfg["LOCKOUT_MINUTES"])
        user.failed_login_attempts = 0  # counter restarts after the lock expires
        log_activity(
            UserActivityLog.Action.ACCOUNT_LOCKED,
            user=user,
            request=request,
            detail=f"Locked for {cfg['LOCKOUT_MINUTES']} minutes",
        )
    user.save(update_fields=["failed_login_attempts", "locked_until"])


def register_successful_login(user: User, request: HttpRequest | None) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = timezone.now()
    user.save(update_fields=["failed_login_attempts", "locked_until", "last_login"])
    log_activity(UserActivityLog.Action.LOGIN_SUCCESS, user=user, request=request)


def blacklist_user_tokens(user: User) -> int:
    """Blacklist every outstanding refresh token for a user (password change,
    deactivation). Returns the number of tokens affected."""
    count = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        count += int(created)
    return count


# ---------------------------------------------------------------- cookies


def set_refresh_cookie(response: HttpResponse, refresh_token: str) -> None:
    cfg = settings.ABIS_AUTH
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        cfg["REFRESH_COOKIE_NAME"],
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=not settings.DEBUG,
        samesite=cfg["REFRESH_COOKIE_SAMESITE"],
        path=cfg["REFRESH_COOKIE_PATH"],
    )


def clear_refresh_cookie(response: HttpResponse) -> None:
    cfg = settings.ABIS_AUTH
    response.delete_cookie(
        cfg["REFRESH_COOKIE_NAME"],
        path=cfg["REFRESH_COOKIE_PATH"],
        samesite=cfg["REFRESH_COOKIE_SAMESITE"],
    )


def get_refresh_from_request(request: HttpRequest) -> str | None:
    """Refresh token from the httpOnly cookie, or request body as a fallback
    for non-browser API clients."""
    raw = request.COOKIES.get(settings.ABIS_AUTH["REFRESH_COOKIE_NAME"])
    if raw:
        return raw
    data = getattr(request, "data", None)
    if isinstance(data, dict):
        return data.get("refresh")
    return None
