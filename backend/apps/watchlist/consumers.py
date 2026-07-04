from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import ALERTS_GROUP

ALLOWED_ROLES = {"admin", "investigator", "supervisor"}


class AlertConsumer(AsyncJsonWebsocketConsumer):
    """ws/alerts/ — realtime watchlist alerts for supervisors/investigators.

    Authentication happens upstream (accounts.ws_auth.JWTAuthMiddleware puts
    the user on the scope); this consumer only gates by role. It must not
    touch the database — role must already be loaded on the user object.
    """

    async def connect(self):
        user = self.scope.get("user")
        role = getattr(user, "role_name", None)
        allowed = bool(
            user
            and user.is_authenticated
            and (user.is_superuser or role in ALLOWED_ROLES)
        )
        if not allowed:
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(ALERTS_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(ALERTS_GROUP, self.channel_name)

    async def alert_created(self, event):
        await self.send_json(event["alert"])
