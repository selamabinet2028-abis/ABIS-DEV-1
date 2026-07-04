"""JWT authentication for WebSocket connections (`?token=<access>`).

The SPA keeps the access token in memory (ADR-006), so WebSockets pass it as
a query parameter; the refresh cookie never reaches ws routes (path-scoped).
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    from apps.accounts.models import User

    user = User.objects.select_related("role").filter(id=user_id).first()
    if user:
        user.role_name  # force-load so consumers never touch the DB
    return user


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        raw_query = scope.get("query_string", b"").decode()
        token = (parse_qs(raw_query).get("token") or [None])[0]
        if token:
            try:
                access = AccessToken(token)
                user = await _get_user(access["user_id"])
                if user and user.is_active:
                    scope["user"] = user
            except (TokenError, KeyError):
                pass
        return await super().__call__(scope, receive, send)
