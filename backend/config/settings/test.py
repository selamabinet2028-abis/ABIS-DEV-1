"""Test settings — pytest runs against these (see backend/pytest.ini)."""

from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-0123456789abcdef-not-for-prod"  # noqa: S105

# Celery runs inline in tests (TEST_STRATEGY.md).
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# No Redis dependency in unit tests.
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# Fast password hashing; throttling off so tests never hit 429.
# (View-level ScopedRateThrottle still reads rates — keep them effectively off.)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/min",
        "user": "10000/min",
        "auth": "10000/min",
        "public": "10000/min",
    },
}

MEDIA_ROOT = BASE_DIR / "test-media"  # noqa: F405
