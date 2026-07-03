"""WebSocket URL routing.

Consumers register here as they land: `ws/alerts/` (T-011 watchlist),
`ws/jobs/{id}/` (T-008 matching).
"""

websocket_urlpatterns: list = []
