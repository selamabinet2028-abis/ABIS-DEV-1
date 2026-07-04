"""Appointment booking: availability + double-booking prevention (ADR-021)."""

from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import Appointment, Station, TimeSlot


def availability(station: Station, date: datetime.date) -> list[dict]:
    """Slots with remaining capacity for one station and date."""
    slots = (
        TimeSlot.objects.filter(station=station, is_active=True)
        .annotate(
            booked=Count(
                "appointments",
                filter=Q(
                    appointments__date=date,
                    appointments__status=Appointment.Status.BOOKED,
                ),
            )
        )
        .order_by("start_time")
    )
    return [
        {
            "slot_id": slot.id,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "capacity": slot.capacity,
            "available": max(slot.capacity - slot.booked, 0),
        }
        for slot in slots
    ]


def book_appointment(
    *,
    station: Station,
    slot: TimeSlot,
    date: datetime.date,
    full_name: str,
    phone: str,
    application=None,
) -> Appointment:
    if not station.is_active:
        raise ValidationError("Station is not accepting bookings.")
    if slot.station_id != station.id or not slot.is_active:
        raise ValidationError("Slot does not belong to this station or is inactive.")
    if date < timezone.localdate():
        raise ValidationError("Booking date must be today or later.")

    with transaction.atomic():
        locked_slot = TimeSlot.objects.select_for_update().get(id=slot.id)
        active = Appointment.objects.filter(
            slot=locked_slot, date=date, status=Appointment.Status.BOOKED
        )
        if active.filter(phone=phone).exists():
            raise ValidationError(
                "This phone number already has a booking for this slot."
            )
        if active.count() >= locked_slot.capacity:
            raise ValidationError("Slot is fully booked for this date.")
        return Appointment.objects.create(
            station=station,
            slot=locked_slot,
            date=date,
            full_name=full_name,
            phone=phone,
            application=application,
        )
