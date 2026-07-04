"""WebSocket URL routing.

`ws/alerts/` — watchlist alerts (T-011). `ws/jobs/{id}/` may land with T-018
if polling proves insufficient.
"""

from django.urls import path

from apps.watchlist.consumers import AlertConsumer

websocket_urlpatterns = [
    path("ws/alerts/", AlertConsumer.as_asgi()),
]
