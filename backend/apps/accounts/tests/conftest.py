import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role

from .factories import DEFAULT_PASSWORD, UserFactory

ROLE_NAMES = [
    Role.ADMIN,
    Role.OPERATOR,
    Role.INVESTIGATOR,
    Role.SUPERVISOR,
    Role.AUDITOR,
]


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def make_user(db):
    """Create a user with a seeded role (roles exist via data migration)."""

    def _make(role_name: str | None = None, password: str = DEFAULT_PASSWORD, **kwargs):
        role = Role.objects.get(name=role_name) if role_name else None
        return UserFactory(role=role, password=password, **kwargs)

    return _make


@pytest.fixture
def auth_client(make_user):
    """APIClient authenticated (force_authenticate) as a user of the given role."""

    def _client(role_name: str | None):
        user = make_user(role_name)
        client = APIClient()
        client.force_authenticate(user=user)
        client.user = user
        return client

    return _client
