"""T-012: public booking — availability, capacity, double-booking prevention."""

import datetime

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment, TimeSlot
from apps.enrollment.tests.factories import StationFactory
from apps.registration.tests.factories import ApplicationFactory

pytestmark = pytest.mark.django_db

PUBLIC_STATIONS = "/api/v1/public/stations/"
PUBLIC_BOOKING = "/api/v1/public/appointments/"


def tomorrow() -> str:
    return (timezone.localdate() + datetime.timedelta(days=1)).isoformat()


@pytest.fixture
def station(db):
    return StationFactory()


@pytest.fixture
def slot(station):
    return TimeSlot.objects.create(
        station=station,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(10, 0),
        capacity=2,
    )


def book(client, station, slot, phone="0911000001", **overrides):
    payload = {
        "station": str(station.id),
        "slot": str(slot.id),
        "date": tomorrow(),
        "full_name": "Test Applicant",
        "phone": phone,
        **overrides,
    }
    return client.post(PUBLIC_BOOKING, payload, format="json")


class TestPublicDiscovery:
    def test_lists_only_active_stations_without_auth(self, api_client, station):
        StationFactory(is_active=False)
        resp = api_client.get(PUBLIC_STATIONS)
        assert resp.status_code == 200
        assert [s["id"] for s in resp.json()] == [str(station.id)]

    def test_slot_availability(self, api_client, station, slot):
        resp = api_client.get(
            f"{PUBLIC_STATIONS}{station.id}/slots/", {"date": tomorrow()}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["capacity"] == 2
        assert body[0]["available"] == 2

    def test_availability_decrements_after_booking(self, api_client, station, slot):
        book(api_client, station, slot)
        body = api_client.get(
            f"{PUBLIC_STATIONS}{station.id}/slots/", {"date": tomorrow()}
        ).json()
        assert body[0]["available"] == 1

    def test_past_date_rejected(self, api_client, station, slot):
        yesterday = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        resp = api_client.get(
            f"{PUBLIC_STATIONS}{station.id}/slots/", {"date": yesterday}
        )
        assert resp.status_code == 400


class TestBooking:
    def test_booking_succeeds_anonymously(self, api_client, station, slot):
        resp = book(api_client, station, slot)
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["status"] == "booked"
        assert body["station_code"] == station.code
        assert body["slot_window"] == "09:00-10:00"

    def test_double_booking_same_phone_rejected(self, api_client, station, slot):
        assert book(api_client, station, slot).status_code == 201
        resp = book(api_client, station, slot)  # same phone, slot, date
        assert resp.status_code == 400
        assert "already has a booking" in resp.json()["detail"]

    def test_capacity_exhaustion_rejected(self, api_client, station, slot):
        assert book(api_client, station, slot, phone="0911000001").status_code == 201
        assert book(api_client, station, slot, phone="0911000002").status_code == 201
        resp = book(api_client, station, slot, phone="0911000003")  # cap = 2
        assert resp.status_code == 400
        assert "fully booked" in resp.json()["detail"]

    def test_cancelled_booking_frees_capacity(
        self, api_client, auth_client, station, slot
    ):
        book(api_client, station, slot, phone="0911000001")
        book(api_client, station, slot, phone="0911000002")

        appointment = Appointment.objects.get(phone="0911000001")
        staff = auth_client("operator")
        resp = staff.patch(
            f"/api/v1/appointments/{appointment.id}/",
            {"status": "cancelled"},
            format="json",
        )
        assert resp.status_code == 200

        assert book(api_client, station, slot, phone="0911000003").status_code == 201

    def test_past_booking_date_rejected(self, api_client, station, slot):
        yesterday = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        resp = book(api_client, station, slot, date=yesterday)
        assert resp.status_code == 400

    def test_slot_of_other_station_rejected(self, api_client, station, slot):
        other_station = StationFactory()
        resp = book(api_client, other_station, slot)
        assert resp.status_code == 400

    def test_booking_links_application_by_tracking_no(self, api_client, station, slot):
        application = ApplicationFactory()
        resp = book(api_client, station, slot, tracking_no=application.tracking_no)
        assert resp.status_code == 201
        assert resp.json()["tracking_no"] == application.tracking_no

    def test_unknown_tracking_no_rejected(self, api_client, station, slot):
        resp = book(api_client, station, slot, tracking_no="PCC-2026-999999")
        assert resp.status_code == 400


class TestStaffEndpoints:
    def test_staff_sees_public_bookings(self, api_client, auth_client, station, slot):
        book(api_client, station, slot)
        listed = auth_client("operator").get("/api/v1/appointments/").json()
        assert listed["count"] == 1

    def test_admin_manages_stations_and_slots(self, auth_client):
        admin = auth_client("admin")
        station_resp = admin.post(
            "/api/v1/stations/",
            {"code": "BES-900", "name": "Adama Station"},
            format="json",
        )
        assert station_resp.status_code == 201
        slot_resp = admin.post(
            "/api/v1/time-slots/",
            {
                "station": station_resp.json()["id"],
                "start_time": "13:00",
                "end_time": "14:00",
                "capacity": 5,
            },
            format="json",
        )
        assert slot_resp.status_code == 201

    def test_slot_window_validation(self, auth_client, station):
        resp = auth_client("admin").post(
            "/api/v1/time-slots/",
            {
                "station": str(station.id),
                "start_time": "15:00",
                "end_time": "14:00",
                "capacity": 5,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_operator_cannot_create_station(self, auth_client):
        resp = auth_client("operator").post(
            "/api/v1/stations/", {"code": "X", "name": "Y"}, format="json"
        )
        assert resp.status_code == 403

    def test_staff_appointments_require_auth(self, api_client, db):
        assert api_client.get("/api/v1/appointments/").status_code == 401
