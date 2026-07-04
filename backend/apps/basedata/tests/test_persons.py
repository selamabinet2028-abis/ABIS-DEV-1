"""T-006: person CRUD/search, RBAC, soft delete, photo upload, audit rows."""

import io

import pytest
from PIL import Image

from apps.audit.models import AuditLog
from apps.basedata.models import Person

from .factories import PersonFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/persons/"

PAYLOAD = {
    "first_name": "Kebede",
    "middle_name": "Alemu",
    "last_name": "Tesfaye",
    "gender": "male",
    "date_of_birth": "1990-05-15",
    "national_id_no": "FIN-1234567890",
    "addresses": [{"region": "Oromia", "zone": "East Shewa", "woreda": "Ada'a"}],
}


def make_photo(name="face.jpg", fmt="JPEG", size=(64, 64)) -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(120, 90, 60)).save(buffer, format=fmt)
    buffer.seek(0)
    buffer.name = name
    return buffer


class TestPersonCrud:
    def test_operator_creates_person_with_generated_number(self, auth_client):
        resp = auth_client("operator").post(URL, PAYLOAD, format="json")
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["person_no"].startswith("P-")
        assert body["full_name"] == "Kebede Alemu Tesfaye"
        # audit row written for the create
        assert AuditLog.objects.filter(
            entity="basedata.Person",
            entity_id=body["id"],
            action=AuditLog.Action.CREATE,
        ).exists()

    def test_person_numbers_are_unique_and_sequential_format(self, make_user):
        p1, p2 = PersonFactory(), PersonFactory()
        assert p1.person_no != p2.person_no
        assert p1.person_no.split("-")[0] == "P"
        assert len(p1.person_no.split("-")[2]) == 6

    def test_update_writes_audit_diff(self, auth_client):
        person = PersonFactory(first_name="Original")
        resp = auth_client("operator").patch(
            f"{URL}{person.id}/", {"first_name": "Corrected"}, format="json"
        )
        assert resp.status_code == 200
        row = (
            AuditLog.objects.filter(
                entity="basedata.Person",
                entity_id=str(person.id),
                action=AuditLog.Action.UPDATE,
            )
            .order_by("-at")
            .first()
        )
        assert row.changes["first_name"] == {"old": "Original", "new": "Corrected"}

    def test_soft_delete_hides_from_list_but_keeps_row(self, auth_client):
        person = PersonFactory()
        client = auth_client("operator")
        assert client.delete(f"{URL}{person.id}/").status_code == 204
        person.refresh_from_db()
        assert person.is_deleted is True
        assert Person.objects.filter(id=person.id).exists()
        ids = [r["id"] for r in client.get(URL).json()["results"]]
        assert str(person.id) not in ids

    def test_blank_national_id_does_not_break_uniqueness(self, auth_client):
        client = auth_client("operator")
        p1 = {**PAYLOAD, "national_id_no": ""}
        p2 = {**PAYLOAD, "national_id_no": ""}
        assert client.post(URL, p1, format="json").status_code == 201
        assert client.post(URL, p2, format="json").status_code == 201  # NULLs coexist

    def test_duplicate_national_id_rejected(self, auth_client):
        client = auth_client("operator")
        assert client.post(URL, PAYLOAD, format="json").status_code == 201
        resp = client.post(URL, PAYLOAD, format="json")
        assert resp.status_code == 400
        assert "national_id_no" in resp.json()

    def test_addresses_must_be_list_of_objects(self, auth_client):
        bad = {**PAYLOAD, "national_id_no": None, "addresses": {"region": "X"}}
        resp = auth_client("operator").post(URL, bad, format="json")
        assert resp.status_code == 400
        assert "addresses" in resp.json()


class TestPersonRbac:
    @pytest.mark.parametrize(
        "role,read,write",
        [
            ("admin", 200, 201),
            ("operator", 200, 201),
            ("investigator", 200, 403),
            ("supervisor", 200, 403),
            ("auditor", 403, 403),
        ],
    )
    def test_matrix(self, auth_client, role, read, write):
        client = auth_client(role)
        assert client.get(URL).status_code == read
        payload = {**PAYLOAD, "national_id_no": None}
        assert client.post(URL, payload, format="json").status_code == write

    def test_anonymous_401(self, api_client, db):
        assert api_client.get(URL).status_code == 401


class TestPersonSearch:
    def test_search_by_name_person_no_and_national_id(self, auth_client):
        target = PersonFactory(first_name="Selam", national_id_no="FIN-XYZ-001")
        PersonFactory(first_name="Other")
        client = auth_client("investigator")

        for term in ["Selam", target.person_no, "FIN-XYZ-001"]:
            results = client.get(URL, {"search": term}).json()["results"]
            assert [r["id"] for r in results] == [str(target.id)], term

    def test_search_writes_audit_row(self, auth_client):
        PersonFactory()
        client = auth_client("investigator")
        client.get(URL, {"search": "Selam"})
        row = AuditLog.objects.filter(
            entity="basedata.Person", action=AuditLog.Action.SEARCH
        ).first()
        assert row is not None
        assert row.changes["query"]["search"] == "Selam"
        assert row.actor_username == client.user.username

    def test_plain_list_without_search_is_not_audited_as_search(self, auth_client):
        PersonFactory()
        auth_client("operator").get(URL)
        assert not AuditLog.objects.filter(
            entity="basedata.Person", action=AuditLog.Action.SEARCH
        ).exists()


class TestPersonPhoto:
    def test_upload_photo_success(self, auth_client):
        person = PersonFactory()
        resp = auth_client("operator").post(
            f"{URL}{person.id}/photo/", {"photo": make_photo()}, format="multipart"
        )
        assert resp.status_code == 200, resp.json()
        person.refresh_from_db()
        assert person.photo.name.startswith(f"persons/photos/{person.id}/")

    def test_upload_rejects_non_image(self, auth_client):
        person = PersonFactory()
        fake = io.BytesIO(b"#!/bin/sh\necho pwned")
        fake.name = "script.jpg"
        resp = auth_client("operator").post(
            f"{URL}{person.id}/photo/", {"photo": fake}, format="multipart"
        )
        assert resp.status_code == 400  # Pillow verification fails

    def test_upload_rejects_disallowed_extension(self, auth_client):
        person = PersonFactory()
        photo = make_photo(name="face.gif", fmt="GIF")
        resp = auth_client("operator").post(
            f"{URL}{person.id}/photo/", {"photo": photo}, format="multipart"
        )
        assert resp.status_code == 400
        assert "photo" in resp.json()

    def test_upload_rejects_oversize(self, auth_client, settings):
        settings.ABIS_MAX_UPLOAD_MB = 0  # everything is too big now
        person = PersonFactory()
        resp = auth_client("operator").post(
            f"{URL}{person.id}/photo/", {"photo": make_photo()}, format="multipart"
        )
        assert resp.status_code == 400

    def test_investigator_cannot_upload(self, auth_client):
        person = PersonFactory()
        resp = auth_client("investigator").post(
            f"{URL}{person.id}/photo/", {"photo": make_photo()}, format="multipart"
        )
        assert resp.status_code == 403
