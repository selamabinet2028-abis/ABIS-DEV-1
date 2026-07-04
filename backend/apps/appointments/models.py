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
