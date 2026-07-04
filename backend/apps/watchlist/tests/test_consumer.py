"""T-011: ws/alerts/ consumer — role gate + group delivery (communicator)."""

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from config.routing import websocket_urlpatterns

pytestmark = pytest.mark.django_db


def _connect_and_maybe_receive(user, message=None):
    """Run the async communicator scenario from a sync test."""

    async def scenario():
        app = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(app, "/ws/alerts/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        received = None
        if connected and message is not None:
            await get_channel_layer().group_send(
                "alerts", {"type": "alert.created", "alert": message}
            )
            received = await communicator.receive_json_from(timeout=2)
        await communicator.disconnect()
        return connected, received

    return async_to_sync(scenario)()


def _preloaded(user):
    user.role_name  # cache the role FK — consumer must not hit the DB
    return user


class TestAlertConsumer:
    def test_investigator_receives_pushed_alert(self, make_user):
        user = _preloaded(make_user("investigator"))
        payload = {"id": "alert-1", "person_name": "Test Person", "score": 100.0}
        connected, received = _connect_and_maybe_receive(user, payload)
        assert connected is True
        assert received == payload

    def test_supervisor_can_connect(self, make_user):
        user = _preloaded(make_user("supervisor"))
        connected, _ = _connect_and_maybe_receive(user)
        assert connected is True

    def test_operator_rejected(self, make_user):
        user = _preloaded(make_user("operator"))
        connected, _ = _connect_and_maybe_receive(user)
        assert connected is False

    def test_anonymous_rejected(self, db):
        connected, _ = _connect_and_maybe_receive(AnonymousUser())
        assert connected is False
