"""Captures the current request in a contextvar so signal receivers can
attribute mutations to an actor/ip/user-agent without threading a request
object through every save()."""

from contextvars import ContextVar

from django.http import HttpRequest

_current_request: ContextVar[HttpRequest | None] = ContextVar(
    "audit_request", default=None
)


def get_current_request() -> HttpRequest | None:
    return _current_request.get()


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)
