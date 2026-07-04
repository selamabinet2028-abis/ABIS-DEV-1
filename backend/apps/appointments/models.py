from django.db import models

from common.models import BaseModel


class Station(BaseModel):
    """Biometric Enrollment Station (BES).

    Minimal at T-007 (Enrollment.station FK needs it); TimeSlot/Appointment
    and public booking land with T-012.
    """

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class TimeSlot(BaseModel):
    """Recurring daily booking window at a station (capacity per date)."""

    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="time_slots"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["station", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["station", "start_time", "end_time"],
                name="uniq_slot_station_window",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.station_id} {self.start_time}-{self.end_time} (cap {self.capacity})"
        )


class Appointment(BaseModel):
    """A booked visit — public booking or staff-created."""

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No show"

    station = models.ForeignKey(
        Station, on_delete=models.PROTECT, related_name="appointments"
    )
    slot = models.ForeignKey(
        TimeSlot, on_delete=models.PROTECT, related_name="appointments"
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.BOOKED
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    application = models.ForeignKey(
        "registration.ClearanceApplication",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )

    class Meta:
        ordering = ["date", "slot__start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["slot", "date", "phone"],
                condition=models.Q(status="booked"),
                name="uniq_active_booking_per_phone",
            )
        ]
        indexes = [models.Index(fields=["station", "date", "status"])]

    def __str__(self) -> str:
        return f"{self.full_name} @ {self.station_id} {self.date} ({self.status})"
