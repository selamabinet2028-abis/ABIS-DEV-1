"""T-009: case CRUD, evidence chain of custody, dashboard, RBAC."""

import io

import pytest

from apps.audit.models import AuditLog
from apps.basedata.tests.factories import InvestigationCategoryFactory

from .factories import CaseFactory, LatentFactory

pytestmark = pytest.mark.django_db

CASES = "/api/v1/cases/"


@pytest.fixture
def investigator(auth_client):
    return auth_client("investigator")


class TestCaseCrud:
    def test_create_generates_case_no(self, investigator):
        category = InvestigationCategoryFactory()
        resp = investigator.post(
            CASES,
            {"title": "Bole burglary", "category": str(category.id)},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["case_no"].startswith("CASE-")
        assert body["category_code"] == category.code
        assert AuditLog.objects.filter(
            entity="investigation.Case",
            entity_id=body["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    def test_case_numbers_unique(self, db):
        a, b = CaseFactory(), CaseFactory()
        assert a.case_no != b.case_no

    def test_patch_status(self, investigator):
        case = CaseFactory()
        resp = investigator.patch(
            f"{CASES}{case.id}/", {"status": "closed"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_search_by_case_no(self, investigator):
        case = CaseFactory(title="Unique Needle")
        CaseFactory()
        results = investigator.get(CASES, {"search": case.case_no}).json()["results"]
        assert [r["id"] for r in results] == [str(case.id)]

    @pytest.mark.parametrize(
        "role,read,write",
        [
            ("admin", 200, 201),
            ("investigator", 200, 201),
            ("supervisor", 200, 403),
            ("operator", 403, 403),
            ("auditor", 403, 403),
        ],
    )
    def test_rbac_matrix(self, auth_client, role, read, write):
        CaseFactory()
        client = auth_client(role)
        assert client.get(CASES).status_code == read
        resp = client.post(CASES, {"title": "Probe"}, format="json")
        assert resp.status_code == write

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(CASES).status_code == 401


class TestEvidence:
    def test_upload_records_chain_of_custody(self, investigator):
        case = CaseFactory()
        upload = io.BytesIO(b"%PDF-1.4 fake report")
        upload.name = "report.pdf"
        resp = investigator.post(
            f"{CASES}{case.id}/evidence/",
            {
                "file": upload,
                "description": "Scene report",
                "collected_by": "Sgt. Almaz T.",
                "collected_at": "2026-07-01T09:30:00Z",
            },
            format="multipart",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["collected_by"] == "Sgt. Almaz T."
        assert len(body["sha256"]) == 64

        listed = investigator.get(f"{CASES}{case.id}/evidence/").json()
        assert len(listed) == 1

    def test_upload_rejects_bad_extension(self, investigator):
        case = CaseFactory()
        upload = io.BytesIO(b"MZ binary")
        upload.name = "malware.exe"
        resp = investigator.post(
            f"{CASES}{case.id}/evidence/",
            {
                "file": upload,
                "collected_by": "X",
                "collected_at": "2026-07-01T00:00:00Z",
            },
            format="multipart",
        )
        assert resp.status_code == 400


class TestDashboard:
    def test_dashboard_aggregates(self, investigator):
        CaseFactory(status="open")
        CaseFactory(status="closed")
        LatentFactory()
        resp = investigator.get(f"{CASES}dashboard/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["cases_total"] == 3  # incl. latent's own case
        assert body["cases_by_status"]["open"] >= 1
        assert body["latents_total"] == 1
        assert "confirmed_latent_hits" in body
