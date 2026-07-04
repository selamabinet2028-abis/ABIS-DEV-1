"""T-006: org units, lookups, investigation categories — CRUD + RBAC."""

import pytest

from apps.audit.models import AuditLog

from .factories import (InvestigationCategoryFactory, LookupValueFactory,
                        OrgUnitFactory)

pytestmark = pytest.mark.django_db


class TestOrgUnits:
    URL = "/api/v1/org-units/"

    def test_admin_builds_hierarchy(self, auth_client):
        client = auth_client("admin")
        root = client.post(self.URL, {"name": "EFPC HQ"}, format="json")
        assert root.status_code == 201
        child = client.post(
            self.URL, {"name": "Forensics", "parent": root.json()["id"]}, format="json"
        )
        assert child.status_code == 201
        assert child.json()["parent_name"] == "EFPC HQ"

        listed = client.get(self.URL, {"parent": root.json()["id"]}).json()["results"]
        assert [r["name"] for r in listed] == ["Forensics"]

    def test_unit_cannot_be_its_own_parent(self, auth_client):
        unit = OrgUnitFactory()
        resp = auth_client("admin").patch(
            f"{self.URL}{unit.id}/", {"parent": str(unit.id)}, format="json"
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "role", ["operator", "investigator", "supervisor", "auditor"]
    )
    def test_non_admin_reads_but_cannot_write(self, auth_client, role):
        OrgUnitFactory()
        client = auth_client(role)
        assert client.get(self.URL).status_code == 200
        assert client.post(self.URL, {"name": "Nope"}, format="json").status_code == 403

    def test_org_unit_create_is_audited(self, auth_client):
        resp = auth_client("admin").post(
            self.URL, {"name": "Audited Unit"}, format="json"
        )
        assert AuditLog.objects.filter(
            entity="basedata.OrgUnit",
            entity_id=resp.json()["id"],
            action=AuditLog.Action.CREATE,
        ).exists()


class TestLookups:
    URL = "/api/v1/lookups/"

    def test_admin_crud_and_category_filter(self, auth_client):
        client = auth_client("admin")
        resp = client.post(
            self.URL,
            {"category": "purpose", "code": "abroad_work", "label": "Work abroad"},
            format="json",
        )
        assert resp.status_code == 201
        LookupValueFactory(category="gender", code="male", label="Male")

        purpose_only = client.get(self.URL, {"category": "purpose"}).json()["results"]
        assert [r["code"] for r in purpose_only] == ["abroad_work"]

    def test_duplicate_category_code_rejected(self, auth_client):
        LookupValueFactory(category="purpose", code="dup", label="First")
        resp = auth_client("admin").post(
            self.URL,
            {"category": "purpose", "code": "dup", "label": "Second"},
            format="json",
        )
        assert resp.status_code == 400

    def test_operator_cannot_write(self, auth_client):
        resp = auth_client("operator").post(
            self.URL, {"category": "x", "code": "y", "label": "z"}, format="json"
        )
        assert resp.status_code == 403


class TestInvestigationCategories:
    URL = "/api/v1/investigation-categories/"

    def test_admin_creates_and_lists(self, auth_client):
        client = auth_client("admin")
        resp = client.post(
            self.URL, {"code": "THEFT", "name": "Theft and burglary"}, format="json"
        )
        assert resp.status_code == 201
        InvestigationCategoryFactory(is_active=False)
        active = client.get(self.URL, {"is_active": "true"}).json()["results"]
        assert [r["code"] for r in active] == ["THEFT"]

    def test_duplicate_code_rejected(self, auth_client):
        InvestigationCategoryFactory(code="DUP")
        resp = auth_client("admin").post(
            self.URL, {"code": "DUP", "name": "Duplicate"}, format="json"
        )
        assert resp.status_code == 400

    def test_investigator_reads_but_cannot_write(self, auth_client):
        client = auth_client("investigator")
        assert client.get(self.URL).status_code == 200
        assert (
            client.post(self.URL, {"code": "X", "name": "Y"}, format="json").status_code
            == 403
        )
