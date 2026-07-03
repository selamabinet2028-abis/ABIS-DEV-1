"""T-001 smoke tests: health endpoint, OpenAPI schema, Swagger UI.

None of these touch the database — they must pass without Postgres running.
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_health_returns_200_ok(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "abis-backend"
    assert "version" in body and "time" in body


def test_health_requires_no_auth(client):
    # No Authorization header on purpose — health is a public liveness probe.
    response = client.get("/api/v1/health/")
    assert response.status_code == 200


def test_openapi_schema_generates(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")


def test_swagger_ui_served(client):
    response = client.get("/api/docs/")
    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
